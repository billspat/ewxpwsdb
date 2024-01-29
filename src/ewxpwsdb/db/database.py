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


# create global engine var
engine = create_engine(url = get_db_url(), echo=True)

def init_db(engine=engine):
    SQLModel.metadata.create_all(engine)

def get_session(engine = engine):
    with Session(engine) as session:
        yield session


