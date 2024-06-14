import pytest, os
import logging
from sqlmodel import select, Session
from sqlalchemy import Engine

from ewxpwsdb.db.importdata import read_station_table
from ewxpwsdb.db.database import init_db, get_db_url, drop_pg_db, create_temp_pg_engine
from ewxpwsdb.db.models import WeatherStation


logging.basicConfig(
    level=os.environ.get('LOGLEVEL', 'DEBUG').upper()
)

def pytest_addoption(parser):

    parser.addoption('--dburl',
                     action='store',
                     default='',
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
    


@pytest.fixture(scope = 'session')
def station_file(request: pytest.FixtureRequest):
    file_path = request.config.getoption("--file")
    if not file_path:
        file_path = 'data/test_stations.tsv'
    
    if not os.path.exists(file_path):
        raise FileExistsError(f"can't find station test data file {file_path}")
    
    return(file_path)


##### Database Fixtures
# the goal of these is to allow test modules to create a temporary test 
# database that is created, filled with data as needed, and deleted when done
# currently only works with SQLite databases.  We will need to find another solution 
# for ephemoral databases with Postgresql 
# TODO consider changing session based on this post:
# https://stackoverflow.com/questions/58660378/how-use-pytest-to-unit-test-sqlalchemy-orm-classes 

@pytest.fixture
def test_host(scope = 'session'):
    # override to test remote hosts
    return 'localhost'


@pytest.fixture(scope = 'session')
def test_db_url(request: pytest.FixtureRequest)->str:
    db_url_param = request.config.getoption("--dburl") 
    db_url = get_db_url(db_url_param) # if dburl param is empty, this fn looks to the environment for a string

    return db_url


@pytest.fixture(scope='session')
def station_type(request: pytest.FixtureRequest)->str:
    return ( request.config.getoption("--station_type").upper() )


# this is a generator function so does not have a return type
@pytest.fixture(scope = 'module')
def db_engine(request: pytest.FixtureRequest, test_db_url: str):

    tmp_db_engine = create_temp_pg_engine(admin_db_url=test_db_url, name_prefix='ewxpws_testdb')
    
    # create tables and initial data in the test database.  If one exists, it may insert new values like stations
    init_db(tmp_db_engine)

    yield tmp_db_engine
    
    temp_db_name = tmp_db_engine.url.database
    temp_db_host = tmp_db_engine.url.host
    tmp_db_engine.dispose()

    db_deleted = drop_pg_db(db_name_to_delete=temp_db_name, admin_db_url=test_db_url)
    
    if not db_deleted:
        print(f"unable to delete db {temp_db_name} on test db host {temp_db_host}")
    
    
@pytest.fixture(scope = 'session')
def db_session(db_engine: Engine):


    with Session(db_engine) as session:
        yield session
        session.close()

    from sqlalchemy.orm import close_all_sessions
    close_all_sessions()
        
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


@pytest.fixture(scope="module")
def test_station_code(station_type, test_station_data)->str:
    """get the first station code of the station type we are testing
       from the test station tsv file used to create our test database, 
       without hitting the database to reduce imports
    """

    test_station_code:str =  [station['station_code'] for station in test_station_data if station['station_type']==station_type][0]
    return test_station_code


@pytest.fixture(scope = 'module')
def db_with_data(db_engine: Engine, request: pytest.FixtureRequest, test_station_data):

    if not request.config.getoption("--no-import"):   
        # station_file = request.config.getoption("--file")
        # # will raise exception if there is a problem
        # import_station_file(station_file, db_engine)
        from ewxpwsdb.db.importdata import import_station_records
        import_station_records(weatherstation_data=test_station_data, engine=db_engine)
    
    yield db_engine

#TODO start with a literal list of types, but copy the technique from ewx_pws package to loop through all types
@pytest.fixture(scope='module')
def weather_station(station_type, db_with_data):
    with Session(db_with_data) as session:
        statement = select(WeatherStation).where(WeatherStation.station_type == station_type)
        results = session.exec(statement)
        weather_station = results.first()
        session.close()

    return(weather_station)

@pytest.fixture(scope = 'function')
def db_with_data_session(db_with_data: Engine):

    with Session(db_with_data) as session:
        yield session
        session.close()
    


