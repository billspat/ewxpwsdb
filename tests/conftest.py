import pytest, os
import logging
from sqlmodel import Session
from sqlalchemy import Engine
from ewxpwsdb.db.importdata import import_station_file, read_station_table
from ewxpwsdb.db.database import init_db, create_engine


def pytest_addoption(parser):

    parser.addoption('--dburl',
                     action='store',
                     default='sqlite:///test-ewxpws.db',
                     help='sqlalchemy db url for test.  If sqlite, is created and then deleted on completion')

    parser.addoption('--file',
                     action='store',
                     default='data/test_stations.tsv',
                     help='tsv file to use for test data')
    
    parser.addoption('--no-import',
                     action='store_true',
                     help='use this to skip importing data (assumes test db already has data)')

    parser.addoption('--echo',
                     action='store_true',
                     help='enable SQL echo-ing')

    parser.addoption('--station_type',
                action='store',
                default = 'SPECTRUM',
                help='station type in all caps')
    


def rm_sqlite_file(db_url):
    import re
    sqlite_prefix = 'sqlite:///'
    if (re.match(sqlite_prefix, db_url)):
        sqlite_file = db_url.replace(sqlite_prefix, '')
        try:
            os.remove(sqlite_file)
        except Exception as e:
            print(f"error deleting {sqlite_file}: {e}")
            return False        
    else:
        print(f"not a sqlite url {db_url}, not deleting")
        return False

    return True

@pytest.fixture(scope = 'module')
def station_file():
    test_file = 'data/test_stations.tsv'
    return(test_file)

##### Database Fixtures
# the goal of these is to allow test modules to create a temporary test 
# database that is created, filled with data as needed, and deleted when done
# currently only works with SQLite databases.  We will need to find another solution 
# for ephemoral databases with Postgresql 
# TODO consider changing session based on this post:
# https://stackoverflow.com/questions/58660378/how-use-pytest-to-unit-test-sqlalchemy-orm-classes 

@pytest.fixture(scope = 'module')
def test_db_url(request: pytest.FixtureRequest)->str:
    return request.config.getoption("--dburl")

# this is a generator function so does not have a return type
@pytest.fixture(scope = 'module')
def db_engine(request: pytest.FixtureRequest, test_db_url: str):
    
    # remove existing file if it's here
    rm_sqlite_file(test_db_url)

    #This fixes all errors except one
    #test_db_url = "sqlite:///:memory:"

    # need to create new test-only db, 
    # would like to use a database.py module method rather than sqlmodel code here explicitly 
    
    if request.config.getoption("--echo"):
        echo_option = True
    else:
        echo_option = False

    engine = create_engine(url = test_db_url, echo=echo_option)
    
    # create the test database
    init_db(engine)

    yield engine
    
    engine.dispose()
    rm_sqlite_file(test_db_url)


@pytest.fixture(scope = 'module')
def db_session(db_engine: Engine):

    with Session(db_engine) as session:
        yield session
        
    # session = Session(db_engine)
    # yield session
    # # remove any changes made to the db
    # session.rollback()
    # session.close()

@pytest.fixture(scope = 'module')
def test_station_data(request: pytest.FixtureRequest):
    station_file = request.config.getoption("--file")
    # check that it exists
    stations = read_station_table(station_file)
    return stations


@pytest.fixture(scope = 'module')
def db_with_data(db_engine: Engine, request: pytest.FixtureRequest):

    if not request.config.getoption("--no-import"):   
        station_file = request.config.getoption("--file")
        # will raise exception if there is a problem
        import_station_file(station_file, db_engine)
    
    yield db_engine

@pytest.fixture(scope = 'module')
def db_with_data_session(db_with_data: Engine):

    with Session(db_with_data) as session:
        yield session

@pytest.fixture(scope='module')
def station_type(request: pytest.FixtureRequest)->str:
    return ( request.config.getoption("--station_type").upper() )
