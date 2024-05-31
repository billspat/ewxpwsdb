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

_EWXPWSDB_URL_VAR = "EWXPWSDB_URL"

def get_db_url(fallback_url:str = '')-> str:
    """get the database connection URL from the environment, or use a parameter if one is sent
    
    Args:
        fallback_url: str, default empty string.  if a URL is here, use that.  otherwise check the environment 
    
    Returns:
        str: string for connecting to db.  This is not checked for validity and may be blank if no url is sent and nothing in the environment
    """

    # consider using local host postgresql
    # fallback_url:str = "postgresql+psycopg2://postgres@localhost:5432/postgres"
    ewxpwsdb_url = fallback_url
    
    if not fallback_url:
        load_dotenv()
        # if env var is not set, this returns 'None' but we want to return empty string
        ewxpwsdb_url = ( os.environ.get(_EWXPWSDB_URL_VAR) or '')
    
    return(ewxpwsdb_url)
    

def check_db_url(db_url:str, echo=False)->bool:
    """checks if SQLAlchemy database URL is valid, e.g. can be used to connect. 

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
    
    return check_engine(engine)


def check_engine(engine:Engine)->bool:
    """You can create a SQL alchemy engine with a wellformed connection string that is not a real database. 
    this checks that a database actually exists for that URL

    Args:
        engine (Engine): SQLAlchemy engine, most likely from create_engine(url)

    Returns:
        bool: True if can connect to the engine, false otherwise
    """

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

    
    if not db_url:
        raise ValueError(f"no database connection string sent and none in the environment. Set the variable {_EWXPWSDB_URL_VAR}")
    
    if "postgres" not in  db_url:
        raise ValueError("not a postgresql connection string, this system requires postgresql")
        
    if not  check_db_url(db_url):
        raise ValueError("not a valid connection string, can't connect to the database")
    
    db_connect_args = {"options": "-c timezone=utc"}
    
    engine = create_engine(url = db_url, 
                           echo=echo, 
                           connect_args=db_connect_args)        

    return engine


def db_name_from_url(db_url:str)->str:
    """extract the just the name of the database from a SQLAlchemy connection URL

    Args:
        db_url (str): a SQLAlchemy URL that includes the database name, e.g. "postgresql+psycopg2://localhost:5432/not_an_actual_database"

    Returns:
        str: the name of the database, or the empty string if there is a problem with the URL
    """

    try:
        engine =  get_engine(db_url)
    except Exception as e:
        Warning('not a valid URL, cannot get the database name')
        return ''

    return str(engine.url.database)



def list_pg_tables(engine)->list[str]:
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

    models = {name:obj for name, obj in python_inspect.getmembers(model_module) if python_inspect.isclass(obj) and hasattr(obj, '__table__')}
    table_names = [k.lower() for k in models.keys()]

    return table_names


def check_db_table_list(engine)->bool:
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
    
    
def init_db(engine, station_tsv_file=None):
    """create new blank tables etc for the db URLin the engine. 
    This requires that the database in the URL already exists on the server in the URL."""

    #TODO add error handling logic here
    # check if the database already exists and if so proceed to try importing
    # check if the database 'server' (postgresql) has a database available

    if not check_engine(engine):    
        raise ValueError(f"could connect to database {engine.url.database}")

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
    

def get_session(engine):
    """ session generator"""

    with Session(engine) as session:
        yield session
        

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

