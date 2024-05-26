"""
this tests checks validity of databse connections and db contents in database.py

"""
from os import getenv
from ewxpwsdb.db.database import Session, engine, check_db, check_db_url
import pytest


# note to test anything other than a default db_url, this test currently requires  --dburl param to the test, loaded into the test_db_url fixture

def test_check_db_url(test_db_url):
    assert check_db_url(test_db_url) == True
    assert check_db_url("not_a_connection_string") == False
    assert check_db_url("postgresql+psycopg2://localhost:5432/not_an_actual_database") == False

    sqlite_url_to_test ='sqlite:///not_a_real_sqlite_file.db' 
    assert check_db_url(sqlite_url_to_test) == True
    from ewxpwsdb.db.database import rm_sqlite_file
    rm_sqlite_file(sqlite_url_to_test)

    


# def test_db_connection(db_engine: Engine):
#     """"""
#     from sqlalchemy import Engine
#     assert isinstance(db_engine, Engine)