"""SQL Database machinery: urls, connection, engines and sessions.  
This reads the OS Environment, or the file .env to get database connection information from 
the variable $EWXPWSDB_URL
"""

from dotenv import load_dotenv
from warnings import warn

import os, logging
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import Engine,create_engine, text, inspect

from ewxpwsdb.db.importdata import import_station_types, import_station_file

def get_db_url(fallback_url = "sqlite:///ewxpws.db" )-> str:
    """get the canonical database connection URL to use with SQL the run, can be overridden with tests
    
    parameters
        fallback_url: str, if nothing is found in the environment, a default URL for dev/test
    
    Returns string for connecting to db.  This is not checked for validity.  
    """
    load_dotenv()
    ewxpwsdb_url = os.environ.get("EWXPWSDB_URL")
    if ewxpwsdb_url:
        return(ewxpwsdb_url)
    else:
        # no matching env variable found, so use the fall back. 
        return(fallback_url)

def check_db_url(db_url:str, echo=False)->bool:
    """checks if SQLAlchemy database URL is valid, e.g. can be used to connect to 

    Args:
        db_url (str): a valid SQLAlchemy connection string

    Returns:
        bool: True if a simple SQL statement can run against the db_url, false if not
    """
    try:
        engine = create_engine(url = db_url, echo = echo)
    except Exception as e:
        # could not even parse the connection string
        return False

    try:
        with engine.connect() as connection:
            result = connection.execute(text('SELECT 1;'))

    except Exception as e:
        return False

    return True


def get_engine(db_url = None, echo = False):
    """ create an engine using sqlmodel and database URL. 
    Sets a connection argument to ask DB not to convert datetimes using the timezone of the server, 
    but always return UTC since datatimes are stored with out timezone info in SQL
    
    Args:
        db_url (str,optional): valid SQLAlchemy db url.  If none sent, calls local function to find one from environment
        echo (boolean, optional):  the 'echo' parameter of the sqlmodel 'create_engine' function.  If true, spits out sql commands emitted, useful for debugging.  Defaults to False    

    Returns:
        SQLAlchemy/sqlmodel Engine for use with a SQLmodel Session() object

    """

    if not db_url:
        db_url = get_db_url()

    #TODO: check if it's a valid SQLalchemy URL.  Regular Expression?
    
    if "postgres" in db_url:
        db_connect_args = {"options": "-c timezone=utc"}
    
    if "sqlite" in db_url:
        db_connect_args = {'check_same_thread':False}

    engine = create_engine(url = db_url, 
                           echo=echo, 
                           connect_args=db_connect_args)        

    return engine
    
# create global engine var for this app.  override this variable. 
engine = get_engine()


def list_pg_tables(engine=engine)->list[str]:
    """get list of tables in database engine, that are data, no catalog or schema tables

    Args:
        engine (Engine, optional): A sqlAlchemy Engine  Defaults to engine global defined in this module.

    Returns:
        list: list of string table names    
    """
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    return table_names

# this could be the source of circular imports as it related to the models, not the database
# but necessary to ensure the database is created correctly. Potentially move this to init py if necessary
def table_classes()->list[str]:
    """for this package, inspects the module with the sqlmodel classes and returns the names of classes that are used for tables, which are those used by sqlmodel package. 

    Returns:
        list[str]: list of names of classes that are tables, which are the names of the tables. 
    """
    import inspect as python_inspect  #  since we importing inspect from sqlalchemy as well
    import ewxpwsdb.db.models as model_module  # for this package, this is the module with all the tables in it
    
    # use inspect to get class, but only those with sqlmodel as super class
    # sqlmodel uses lower case for actual table names since mixed case names must be quoted in postgresql
    # p.s. mypy can't handle this one
    tables = [name.lower() for name, obj in python_inspect.getmembers(model_module) if python_inspect.isclass(obj) and obj.__class__.__name__ == 'SQLModelMetaclass']  #ignore type
    return tables


def check_db_table_list(engine=engine)->bool:
    """check that database at engine is present and has tables in it.  
    This does not check if the fields are create 
    
    Returns:
        bool:  True is there is a table created in the engine for each models.  
    """
    
    if check_db_url(engine.url) == False:
        Warning('unable to connect with given URL')
        return False
    
    tables_in_db = list_pg_tables(engine)
    tables_defined = table_classes()
    return set(tables_in_db) == set(tables_defined)
    
    
##### NEED A LIST OF THE TABLES IN THIS DATABASE THAT ARE NOT JUST CATALOG TABLES


def init_db(engine=engine, station_tsv_file=None):
    """create new blank tables etc for the db URLin the engine. 
    This requires that the database in the URL already exists on the server in the URL."""

    #TODO add error handling logic here
    # check if we are using sqlite
    # check if the database already exists and if so procede to try importing
    # check if the database 'server' (postgresql) has a database available

    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        logging.error(f"error creating new database: {e}")
        raise(e)

    
    # check if there are tables and if so then proceed with import
    # TODO in the function below, check if the station types have already been imported, if so skip
    import_station_types(engine)

    if station_tsv_file:
        if os.path.exists(station_tsv_file):
            import_station_file(station_tsv_file, engine)
        else:
            raise ValueError(f"could not import data, station tsv file for import not found: {station_tsv_file}")
            #TODO this leaves database in partial state, tables with no stations
    
    

def get_session(engine = engine):
    """ session generator"""

    with Session(engine) as session:
        yield session


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

def list_pg_databases(admin_db_url)->list[str]|None:
    """get list of tables from pg tables, includes tables from all schema.  assumes the database is accessible without a password 
    list the MacOS postgres.app
    
    Args:
        host (str, optional): the host where the postgresql server is running . Defaults to 'localhost'.
        
    Returns
        list[str]|None: list of database names from all schema if the db can be connected to, or None if there was any problem connecting 
    """

    try:
        with create_engine(admin_db_url, isolation_level='AUTOCOMMIT').connect() as connection:
                result = connection.execute(text('SELECT datname FROM pg_database')).fetchall()
                tablelist = [row[0] for row in result]
    except Exception as e:
        warn(f"could not get list of databases from dburl: {e}")
        return None

    return(tablelist)


def temp_pg_engine(name_prefix:str='ewxpws_testdb', host:str='localhost')->Engine:
    """generate a random database name, and create an empty database with that name

    Args:
        name_prefix (str, optional): a human name prefix identifying the purpose of this db when the db is inspected. Defaults to 'ewxpws_testdb'.  
        host (str, optional): the host where the postgresql server is running . Defaults to 'localhost'.

    Returns:
        Engine: sqlmodel engine that can be used in a session.  given the engine one can find the db name if necessary
    """
    ## generate a db name
    import string, secrets
    letters = string.ascii_lowercase+string.ascii_uppercase+string.digits            
    random_suffix:str =  ''.join(secrets.choice(letters) for i in range(10))

    temp_db_name:str = (f"{name_prefix}_{random_suffix}").lower()
    
    # create an empty postgresql database
    # this URL works with postgres.app on MacOS which does not require passwords   Need to test on Postgresql linux, windows or some other install on mac
    admin_db_url = f"postgresql+psycopg2://postgres@{host}:5432/postgres"

    with create_engine(admin_db_url,
        isolation_level='AUTOCOMMIT').connect() as connection:
            connection.execute(text(f"CREATE DATABASE {temp_db_name}"))

    temp_db_url:str = f"postgresql+psycopg2://{host}:5432/{temp_db_name}"
    
    # use our local function for connecting to the db, which may set options
    engine = get_engine(db_url= temp_db_url, echo = False)
    return(engine)


def drop_temp_pg_engine(engine, host='localhost'):
    """ given an engine, drop the postgresql temp database """
    # all sessions must be closed

    # get the db name from the engine
    temp_db_url = engine.url
    if 'postgresql' not in temp_db_url.drivername:
        warn('engine is not for Postgresql, cancelling')
        return False

    # format "postgresql+psycopg2://{host}:5432/{test_db_name}"
    temp_db_name = engine.url.database
    engine.dispose()
    result = drop_temp_pg_db(temp_db_name, host=host)

    return(result)

    # TODO check that it's gone 

def drop_temp_pg_db(temp_db_name, host='localhost'):
    
    if temp_db_name not in list_pg_databases(host):
        warn(f"database {temp_db_name} not found in postgresql on {host}, can't delete")
        return False
    
    admin_db_url = f"postgresql+psycopg2://postgres@{host}:5432/postgres"

    try:
        with create_engine(admin_db_url,
            isolation_level='AUTOCOMMIT').connect() as connection:
                connection.execute(text(f"DROP DATABASE {temp_db_name}"))
    except Exception as e:
        warn(f"could not drop database {temp_db_name}: {e}")
        return False
    
    return True

