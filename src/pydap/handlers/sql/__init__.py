"""
Pydap SQL handler.

This handler allows Pydap to server data from any relational database supported
by SQLAlchemy. Each dataset is represented by a YAML file that defines the 
database connection, variables and other associated metadata. Here's a simple
example:

    database:
        dsn: 'sqlite:///simple.db'
        table: test

    dataset:
        NC_GLOBAL:
            history: Created by the Pydap SQL handler

        contact: roberto@dealmeida.net
        name: test_dataset
        owner: Roberto De Almeida
        version: 1.0
        last_modified: !Query 'SELECT time FROM test ORDER BY time DESC LIMIT 1;'

    sequence:
        name: simple
        items: !Query 'SELECT COUNT(id) FROM test'

    _id:
        col: id
        long_name: sequence id
        missing_value: -9999

    lon:
        col: lon
        axis: X
        grads_dim: x
        long_name: longitude
        units: degrees_east
        missing_value: -9999
        global_range: [-180, 180]
        valid_range: !Query 'SELECT min(lon), max(lon) FROM test'

"""
import os
import itertools
import re
import ast
from datetime import datetime
import time
from email.utils import formatdate

from sqlalchemy import create_engine
from sqlalchemy.engine import RowProxy
import yaml

from pydap.model import *
from pydap.lib import fix_slice, quote
from pydap.handlers.lib import BaseHandler
from pydap.handlers.csv import CSVHandler, CSVSequenceType, CSVBaseType
from pydap.exceptions import OpenFileError, ConstraintExpressionError


# module level engines, using connection pool
class EngineCreator(dict):
    def __missing__(self, key):
        self[key] = create_engine(key)
        return self[key]
Engines = EngineCreator()


class SQLHandler(CSVHandler):
    def __init__(self, filepath):
        BaseHandler.__init__(self)
        self.filepath = filepath

        try:
            with open(filepath, 'Ur') as fp:
                fp = open(filepath, 'Ur')
                self.config = yaml.load(fp)
        except Exception, exc:
            message = 'Unable to open file {filepath}: {exc}'.format(filepath=self.filepath, exc=exc)
            raise OpenFileError(message)

        # add last modified from config
        try:
            last_modified = self.config['dataset']['last_modified']
            if isinstance(last_modified, RowProxy):
                last_modified = last_modified[0]  # !Query
            if isinstance(last_modified, basestring):
                last_modified = datetime.strptime(last_modified, '%Y-%m-%d %H:%M:%S')
            self.additional_headers.append(
                    ('Last-modified', formatdate( time.mktime( last_modified.timetuple() ) )))
        except KeyError:
            pass

        #self.additional_headers XXX

    def parse(self, projection, selection):
        """
        Parse the constraint expression and return a dataset.

        """
        # create the dataset 
        attrs = self.config.get('dataset', {}).copy()
        name = attrs.pop('name', os.path.split(self.filepath)[1])
        dataset = DatasetType(name, attrs)

        # and now create the sequence
        attrs = self.config.get('sequence', {}).copy()
        name = attrs.pop('name', 'sequence')
        seq = dataset[quote(name)] = SQLSequenceType(name, self.config, attrs)

        # apply selection
        seq.selection.extend(selection)

        # by default, return all columns
        cols = (key for key in self.config if 'col' in self.config[key])

        # apply projection
        if projection:
            # fix shorthand notation in projection; some clients will request
            # `child` instead of `sequence.child`.
            for var in projection:
                if len(var) == 1 and var[0][0] != seq.name:
                    var.insert(0, (seq.name, ()))

            # get all slices and apply the first one, since they should be equal
            slices = [ fix_slice(var[0][1], (None,)) for var in projection ]
            seq.slice = slices[0]

            # check that all slices are equal
            if any(slice_ != seq.slice for slice_ in slices[1:]):
                raise ConstraintExpressionError('Slices are not unique!')

            # if the sequence has not been directly requested, return only
            # those variables that were requested
            if all(len(var) == 2 for var in projection):
                cols = [ var[1][0] for var in projection ]

        # add variables
        for col in cols:
            attrs = {k : v for k, v in self.config[col].items() if k != 'col'}
            seq[quote(col)] = SQLBaseType(col, attributes=attrs)

        return dataset


class SQLSequenceType(CSVSequenceType):
    """
    A `SequenceType` that reads data from an SQL database.

    Here's a standard dataset for testing sequential data:

        >>> data = [
        ... (10, 15.2, 'Diamond_St'), 
        ... (11, 13.1, 'Blacktail_Loop'),
        ... (12, 13.3, 'Platinum_St'),
        ... (13, 12.1, 'Kodiak_Trail')]

        >>> import os
        >>> if os.path.exists('test.db'):
        ...     os.unlink('test.db')
        >>> import sqlite3
        >>> conn = sqlite3.connect('test.db')
        >>> c = conn.cursor()
        >>> out = c.execute("CREATE TABLE test (idx real, temperature real, site text)")
        >>> out = c.executemany("INSERT INTO test VALUES (?, ?, ?)", data)
        >>> conn.commit()
        >>> c.close()

    Iteraring over the sequence returns data:

        >>> config = {
        ...     'database': { 'dsn': 'sqlite:///test.db', 'table': 'test', 'order': 'idx' },
        ...     'index': { 'col': 'idx' },
        ...     'temperature': { 'col': 'temperature' },
        ...     'site': { 'col': 'site' }}

        >>> seq = SQLSequenceType('example', config)
        >>> seq['index'] = SQLBaseType('index')
        >>> seq['temperature'] = SQLBaseType('temperature')
        >>> seq['site'] = SQLBaseType('site')

        >>> for line in seq:
        ...     print line
        (10.0, 15.2, u'Diamond_St')
        (11.0, 13.1, u'Blacktail_Loop')
        (12.0, 13.3, u'Platinum_St')
        (13.0, 12.1, u'Kodiak_Trail')

        >>> for line in seq['temperature', 'site', 'index']:
        ...     print line
        (15.2, u'Diamond_St', 10.0)
        (13.1, u'Blacktail_Loop', 11.0)
        (13.3, u'Platinum_St', 12.0)
        (12.1, u'Kodiak_Trail', 13.0)

    We can iterate over children:

        >>> for line in seq['temperature']:
        ...     print line
        15.2
        13.1
        13.3
        12.1

    We can filter the data:

        >>> for line in seq[ seq.index > 10 ]:
        ...     print line
        (11.0, 13.1, u'Blacktail_Loop')
        (12.0, 13.3, u'Platinum_St')
        (13.0, 12.1, u'Kodiak_Trail')

        >>> for line in seq[ seq.index > 10 ]['site']:
        ...     print line
        Blacktail_Loop
        Platinum_St
        Kodiak_Trail

        >>> for line in seq['site', 'temperature'][ seq.index > 10 ]:
        ...     print line
        (u'Blacktail_Loop', 13.1)
        (u'Platinum_St', 13.3)
        (u'Kodiak_Trail', 12.1)

    Or slice it:

        >>> for line in seq[::2]:
        ...     print line
        (10.0, 15.2, u'Diamond_St')
        (12.0, 13.3, u'Platinum_St')

        >>> for line in seq[ seq.index > 10 ][::2]['site']:
        ...     print line
        Blacktail_Loop
        Kodiak_Trail

        >>> for line in seq[ seq.index > 10 ]['site'][::2]:
        ...     print line
        Blacktail_Loop
        Kodiak_Trail

    """
    def __init__(self, name, config, attributes=None, **kwargs):
        StructureType.__init__(self, name, attributes, **kwargs)
        self.config = config
        self.selection = []
        self.slice = (slice(None),)
        self.sequence_level = 1

    @property
    def query(self):
        # mapping between variable names and their columns
        mapping = {key : self.config[key]['col'] for key in self.config if 'col' in self.config[key]}

        return "SELECT {cols} FROM {table} {where} ORDER BY {order} LIMIT {limit} OFFSET {offset}""".format(
                cols=', '.join(self.config[key]['col'] for key in self.keys()),
                table=self.config['database']['table'],
                where=parse_queries(self.selection, mapping),
                order=self.config['database'].get('order', 'id'),
                limit=(self.slice[0].stop or sys.maxint)-(self.slice[0].start or 0),
                offset=self.slice[0].start or 0)

    def __iter__(self):
        conn = Engines[self.config['database']['dsn']].connect()
        data = conn.execute(self.query)

        # there's no standard way of choosing every n result from a query using 
        # SQL, so we need to filter it on Python side
        data = itertools.islice(data, 0, None, self.slice[0].step)

        for row in data:
            yield row

        conn.close()

    def clone(self):
        out = self.__class__(self.name, self.config, self.attributes.copy())
        out.id = self.id
        out.sequence_level = self.sequence_level

        out.selection = self.selection[:]

        # Clone children too.
        for child in self.children():
            out[child.name] = child.clone()

        return out


class SQLBaseType(CSVBaseType):
    pass


def parse_queries(selection, mapping):
    out = []
    for expression in selection:
        id1, op, id2 = re.split('(<=|>=|!=|=~|>|<|=)', expression, 1)

        # a should be a variable in the children
        name1 = id1.split('.')[-1]
        if name1 in mapping:
            a = mapping[name1]
        else:
            raise ConstraintExpressionError(
                    'Invalid constraint expression: "{expression}" ("{id}" is not a valid variable)'.format(
                    expression=expression, id=id1))

        # b could be a variable or constant
        name2 = id2.split('.')[-1]
        if name2 in mapping:
            b = mapping[name2]
        else:
            b = ast.literal_eval(name2)

        out.append('({} {} {})'.format(a, op, b))

    condition = ' AND '.join(out)
    if condition:
        condition = 'WHERE {}'.format(condition)

    return condition


def yaml_query(loader, node):
    # read DSN
    for obj in [obj for obj in loader.constructed_objects if isinstance(obj, yaml.MappingNode)]:
        try:
            mapping = loader.construct_mapping(obj)
            dsn = mapping['dsn']
            break
        except:
            pass

    # get/set connection
    conn = Engines[dsn].connect()

    query = loader.construct_scalar(node)
    results = conn.execute(query).fetchone()
    conn.close()
    return results

yaml.add_constructor('!Query', yaml_query)


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    import sys
    from paste.httpserver import serve

    _test()

    application = SQLHandler(sys.argv[1])
    serve(application, port=8001)
