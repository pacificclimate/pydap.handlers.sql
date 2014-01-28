import os
from tempfile import NamedTemporaryFile
from StringIO import StringIO

from pydap.handlers.sql import SQLHandler

from sqlalchemy import create_engine
import pytest
from webob.request import Request

@pytest.fixture
def testdb(request):
  with NamedTemporaryFile('w', delete=False) as f:
    engine = create_engine('sqlite:///' + f.name, echo=True)
    engine.execute("CREATE TABLE mytable (foo INTEGER);")
    fname = f.name

  def fin():
    os.remove(fname)
  request.addfinalizer(fin)
  return fname

@pytest.fixture
def testconfig(testdb, request):
  config = '''database:
  dsn: "sqlite:///{0}"
  id: "mytable"
  table: "mytable"

dataset:
  NC_GLOBAL:
    name: "test dataset"

sequence:
  name: "a_sequence"

foo:
  col: "foo"
  type: Integer
'''.format(testdb)

  with NamedTemporaryFile('w', delete=False) as myconfig:
    myconfig.write(config)
    fname = myconfig.name

  def fin():
    os.remove(fname)
  request.addfinalizer(fin)
  return fname


def test_nodata(testconfig):

  handler = SQLHandler(testconfig)
  req = Request.blank('/foo.sql.das')
  assert handler
  assert handler.dataset
  
  resp = req.get_response(handler)
  assert resp.status == '200 OK'
  assert resp.body == '''Attributes {
    NC_GLOBAL {
        String name "test dataset";
    }
    a_sequence {
        foo {
            String type "Integer";
        }
    }
}
'''
