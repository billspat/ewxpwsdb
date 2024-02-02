"""SQL Database machinery: urls, connection, engines and sessions.  
This reads the OS Environment, or the file .env to get database connection information from 
the variable $EWXPWSDB_URL
"""

from dotenv import load_dotenv
import os, logging
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import Engine

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
    
    engine = create_engine(url = db_url, 
                           echo=echo, 
                           connect_args={"options": "-c timezone=utc"})        

    return engine
    
# create global engine var for this app.  override this variable. 
engine = get_engine()

def check_db(engine=engine):
    """check that database at engine is present and has tables in it. """
    return True


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