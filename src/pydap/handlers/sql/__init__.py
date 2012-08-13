from pydap.handlers.csv import CSVHandler, CSVSequenceType


class SQLHandler(CSVHandler):
    def __init__(self, filepath):
        pass


class SQLSequence(CSVSequenceType):
    """
    A `SequenceType` that reads data from an SQL database.

    Here's a standard dataset for testing sequential data:

        >>> data = [
        ... (10, 15.2, 'Diamond_St'), 
        ... (11, 13.1, 'Blacktail_Loop'),
        ... (12, 13.3, 'Platinum_St'),
        ... (13, 12.1, 'Kodiak_Trail')]

        >>> import os
        >>> os.unlink('test.db')
        >>> import sqlite3
        >>> conn = sqlite3.connect('test.db')
        >>> c = conn.cursor()
        >>> out = c.execute("CREATE TABLE test (idx real, temperature real, site text)")
        >>> out = c.executemany("INSERT INTO test VALUES (?, ?, ?)", data)
        >>> conn.commit()
        >>> c.close()

    Iteraring over the sequence returns data:

        >>> seq = SQLSequenceType('example', 'test.csv')
        >>> seq['index'] = SQLBaseType('index')
        >>> seq['temperature'] = SQLBaseType('temperature')
        >>> seq['site'] = SQLBaseType('site')

        >>> for line in seq:
        ...     print line
        [10.0, 15.2, 'Diamond_St']
        [11.0, 13.1, 'Blacktail_Loop']
        [12.0, 13.3, 'Platinum_St']
        [13.0, 12.1, 'Kodiak_Trail']

    """
    def __iter__(self):
        pass


def _test():
    import doctest
    doctest.testmod()


if __name__ == "__main__":
    import sys
    from paste.httpserver import serve

    _test()

    #application = CSVHandler(sys.argv[1])
    #serve(application, port=8001)
