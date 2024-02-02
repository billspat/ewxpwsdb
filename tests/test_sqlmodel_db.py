#!/usr/bin/env python

from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy import Engine
import pytest
from pydantic import ValidationError
from ewxpwsdb.db.database import Session
from ewxpwsdb.db.models import WeatherStation, StationType

from sqlmodel import select

def test_db_connection(db_engine: Engine):
    """"""
    from sqlalchemy import Engine
    assert isinstance(db_engine, Engine)


def test_that_the_db_has_tables(db_engine: Engine):
    """Tables in the database are created when db_engine fixture is made.   """

    from sqlalchemy import inspect
    inspector = inspect(db_engine)
    created_db_tables = list(inspector.get_table_names())
    for expected_table in ['WeatherStation', 'Reading', 'stationtype','APIResponse']:
        assert expected_table.lower() in created_db_tables

def test_that_station_types_has_entries_after_init(db_engine: Engine):
    # db_engine fixture runs db_init that should create station types

    with Session(db_engine) as session:
        statement = select(StationType)
        results = session.exec(statement)
        station_types = results.all()

    assert station_types is not None
    assert len(station_types) > 2

    
    from ewxpwsdb.weather_apis import STATION_TYPE_LIST
    for st in station_types:
        assert st.station_type in STATION_TYPE_LIST


def test_import_of_data(db_with_data: Any):
    """ test that this fixture actually imports data.  uses command line arg for file source"""
    with Session(db_with_data) as session:
        statement = select(WeatherStation)
        results = session.exec(statement)
        stations = results.all()    
        assert len(stations)> 0
        # check that there is data in all the fields

def test_duplicate_insert(db_with_data: Any, test_station_data: dict):
    # insert a dup.  must be run after the db has data
    dup_station = test_station_data[2]
    dup_ws = WeatherStation.model_validate(dup_station)

    with pytest.raises(IntegrityError):
        with Session(db_with_data) as session:
            session.add(dup_ws)
            session.commit()

    # we shouldn't get to this
    assert(True)



