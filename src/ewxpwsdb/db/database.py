from sqlmodel import SQLModel, create_engine, Session
from dotenv import load_dotenv
import os

# TODO use factory pattern instead of globals


def get_db_url(fallback_url = "sqlite:///ewxpws.db" ):
    """ stub that will ultimately provide single place for logic to """
    load_dotenv()
    # this is a relative URL, so really depends on where this is run! 
    

    ewxpwsdb_url = os.environ.get("EWXPWSDB_URL")
    if ewxpwsdb_url:
        return(ewxpwsdb_url)
    else:
        return(fallback_url)

def get_engine(db_url = None):
    """ create an engine, and ask DB not to convert datetimes using timezone of the server, but always assume UTC"""

    if not db_url:
        db_url = get_db_url()

    engine = create_engine(url = db_url, 
                           echo=True, 
                           connect_args={"options": "-c timezone=utc"})        

    return engine
    
# create global engine var, override as necessary
engine = get_engine()

def init_db(engine=engine):
    """create new blank tables etc for the db URLin the engine. 
    This requires that the database in the URL already exists on the server in the URL"""
    SQLModel.metadata.create_all(engine)

def get_session(engine = engine):
    with Session(engine) as session:
        yield session


