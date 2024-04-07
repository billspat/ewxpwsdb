import pytest

from ewxpwsdb.db.database import temp_pg_engine, drop_temp_pg_engine, list_pg_databases, init_db
from sqlalchemy import Engine, inspect
# from sqlalchemy.engine.reflection import Inspector


@pytest.fixture
def test_host():
    # override to test remote hosts
    return 'localhost'

def test_db_list(test_host):
    all_dbs = list_pg_databases(test_host)
    assert isinstance(all_dbs, list)
    assert 'postgres' in all_dbs


def test_can_create_and_delete_temp_postgresql_db(test_host):

    tmp_engine = temp_pg_engine(host=test_host)
    assert isinstance(tmp_engine, Engine)

    result = init_db(tmp_engine)
    inspector = inspect(tmp_engine)
    table_names = inspector.get_table_names()
    assert 'reading' in table_names
    assert 'weatherstation' in table_names

    temp_db_name = tmp_engine.url.database
    all_dbs = list_pg_databases(test_host)
    assert all_dbs is not None
    assert temp_db_name in all_dbs
    
    result_of_drop = drop_temp_pg_engine(tmp_engine, test_host)
    assert result_of_drop

    all_dbs_after_drop = list_pg_databases(test_host)
    assert temp_db_name not in all_dbs_after_drop
    
    tmp_engine.dispose()







    




