import pytest

from ewxpwsdb.db.database import create_temp_pg_engine, drop_pg_db, list_pg_databases, init_db
from sqlalchemy import Engine, inspect
# from sqlalchemy.engine.reflection import Inspector


def test_db_list(test_db_url):
    all_dbs = list_pg_databases(test_db_url)
    assert isinstance(all_dbs, list)
    assert 'postgres' in all_dbs


def test_can_create_and_delete_temp_postgresql_db(test_db_url):

    tmp_engine = create_temp_pg_engine(admin_db_url=test_db_url, name_prefix='ewxpws_test_test')
    assert isinstance(tmp_engine, Engine)
    
    result = init_db(tmp_engine)
    inspector = inspect(tmp_engine)
    table_names = inspector.get_table_names()
    assert 'reading' in table_names
    assert 'weatherstation' in table_names

    temp_db_name = tmp_engine.url.database
    all_dbs = list_pg_databases(test_db_url)
    assert all_dbs is not None
    assert temp_db_name in all_dbs
    
    tmp_engine.dispose()
    result_of_drop = drop_pg_db(db_name_to_delete=temp_db_name, admin_db_url=test_db_url)
    assert result_of_drop

    all_dbs_after_drop = list_pg_databases(test_db_url)
    assert temp_db_name not in all_dbs_after_drop
    
    tmp_engine.dispose()







    




