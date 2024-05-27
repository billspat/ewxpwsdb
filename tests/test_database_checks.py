"""
this tests checks validity of databse connections and db contents in database.py

"""
from os import getenv
from ewxpwsdb.db.database import Session, get_engine,  check_db_url, get_engine,list_pg_tables, check_db_table_list
import pytest

@pytest.fixture
def test_engine(test_db_url):
    engine =  get_engine(test_db_url)
    yield engine
    engine.dispose()

# note to test anything other than a default db_url, this test currently requires  --dburl param to the test, loaded into the test_db_url fixture

def test_check_db_url(test_db_url):
    assert check_db_url(test_db_url) == True
    assert check_db_url("not_a_connection_string") == False
    assert check_db_url("postgresql+psycopg2://localhost:5432/not_an_actual_database") == False

    sqlite_url_to_test ='sqlite:///not_a_real_sqlite_file.db' 
    assert check_db_url(sqlite_url_to_test) == True
    from ewxpwsdb.db.database import rm_sqlite_file
    rm_sqlite_file(sqlite_url_to_test)


def test_postrgresql_table_list(test_engine):
    """can we get the list of tables from a postgresql database?"""
    if not 'postgresql' in str(test_engine.url):
        Warning("db url is not for postgreql, can't test pg functions")
        assert False
        return
    tbl_list = list_pg_tables(test_engine)
    assert isinstance(tbl_list, list)
    assert len(tbl_list) > 0
    # TODO - create table, check that it's in the list, delete the table (idempotent)


def test_get_package_tables():
    # just ensuring this function doesn't crash as returns one of the tables we expect to see
    # not testing for all tables as we'd have to keep it up to date during development
    from ewxpwsdb.db.database import table_classes

    model_list = table_classes()
    assert isinstance(model_list, list)
    assert 'reading' in model_list
    
def test_check_db_table_list(test_engine):
    # for this test to pass
    # TODO : create a temp db and use init_db to fill it up to guarantee is the has the correct table list
    assert check_db_table_list(test_engine)
