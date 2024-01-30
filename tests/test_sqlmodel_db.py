#!/usr/bin/env python

from sqlalchemy.exc import IntegrityError

import pytest, os
from pydantic import ValidationError
from ewxpwsdb.db.database import Session, init_db, engine, get_session, create_engine
from ewxpwsdb.db.models import WeatherStation, Reading
from ewxpwsdb.db.importdata import import_station_file, read_station_table


from sqlmodel import select

# global var override engine to use test db
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
def test_db_url(request):
    return request.config.getoption("--dburl")

@pytest.fixture(scope = 'module')
def db_engine(test_db_url):
    # need to create new test-only db, 
    # would like to use a database.py module method rather than sqlmodel code here explicitly 
    engine = create_engine(url = test_db_url, echo=True)
    # create the test database
    init_db(engine)
    yield engine
    engine.dispose()
    rm_sqlite_file(test_db_url)


@pytest.fixture(scope = 'module')
def db_session(db_engine):
    session = Session(db_engine)
    yield session
    # remove any changes made to the db
    session.rollback()
    session.close()

@pytest.fixture(scope = 'module')
def test_station_data(request):
    station_file = request.config.getoption("--file")
    # check that it exists
    stations = read_station_table(station_file)
    return stations


@pytest.fixture(scope = 'module')
def db_with_data(db_engine, request):
    if not request.config.getoption("--no-import"):   
        station_file = request.config.getoption("--file")
        # will raise exception if there is a problem
        import_station_file(station_file, db_engine)
        yield db_engine

        # there is no roll back from this, data just gets imported
        # BUT could delete all the data if we wanted


def test_db_connection(db_engine):
    """"""
    from sqlalchemy import Engine
    assert isinstance(db_engine, Engine)


def test_that_the_db_has_tables(db_engine):
    """Tables in the database are created when db_engine fixture is made.   """

    from sqlalchemy import inspect
    inspector = inspect(db_engine)
    created_db_tables = list(inspector.get_table_names())
    for expected_table in ['WeatherStation', 'Reading', 'stationtype']:
        assert expected_table.lower() in created_db_tables

def test_import_of_data(db_with_data):
    """ test that this fixture actually imports data.  uses command line arg for file source"""
    with Session(db_with_data) as session:
        statement = select(WeatherStation)
        results = session.exec(statement)
        stations = results.all()    
        assert len(stations)> 0
        # check that there is data in all the fields

def test_duplicate_insert(db_with_data, test_station_data):
    # insert a dup.  must be run after the db has data
    dup_station = test_station_data[2]
    dup_ws = WeatherStation.model_validate(dup_station)

    with pytest.raises(IntegrityError):
        with Session(db_with_data) as session:
            session.add(dup_ws)
            session.commit()

    # we shouldn't get to this
    assert(True)

