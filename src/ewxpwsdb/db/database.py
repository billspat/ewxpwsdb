"""SQL Database machinery: urls, connection, engines and sessions.  
This reads the OS Environment, or the file .env to get database connection information from 
the variable $EWXPWSDB_URL
"""

from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
import os


def get_db_url(fallback_url = "sqlite:///ewxpws.db" )-> str:
    """get the canonical database connection URL to use with SQL the run, can be overridden with tests
    
    parameters
        fallback_url: str, if nothing is found in the environment, a default URL for dev/test
    """
    load_dotenv()
    ewxpwsdb_url = os.environ.get("EWXPWSDB_URL")
    if ewxpwsdb_url:
        return(ewxpwsdb_url)
    else:
        # no matching env variable found, so use the fall back. 
        return(fallback_url)


def get_engine(db_url = None):
    """ create an engine, and ask DB not to convert datetimes using timezone of the server, but always assume UTC"""

    if not db_url:
        db_url = get_db_url()

    engine = create_engine(url = db_url, 
                           echo=True, 
                           connect_args={"options": "-c timezone=utc"})        

    return engine
    
# create global engine var for this app.  override this variable. 
engine = get_engine()

def init_db(engine=engine):
    """create new blank tables etc for the db URLin the engine. 
    This requires that the database in the URL already exists on the server in the URL."""
    SQLModel.metadata.create_all(engine)

def get_session(engine = engine):
    """ session generator"""

    with Session(engine) as session:
        yield session


