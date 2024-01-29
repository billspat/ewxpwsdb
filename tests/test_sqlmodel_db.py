#!/usr/bin/env python

from sqlalchemy.exc import IntegrityError

import pytest, os
from pydantic import ValidationError
from ewxpwsdb.db.database import Session, init_db, engine, get_session, create_engine
from ewxpwsdb.db.models import WeatherStation, Reading
from ewxpwsdb.db.importdata import import_station_table, read_station_table

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


        
    
            


# @pytest.mark.xfail(raises=IntegrityError)
# def test_duplicate_insert(db):
#     # insert a dup.  must be run after the db has data

#     pass

