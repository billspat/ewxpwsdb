"""Utilites to import data for the database. 
The import datafile _must_ be tab delimited
 Note that in Python 3.11, the dict reader seems to be broken.  
If using single quotes as a quote character, the reader _still_ splits the line on commas even if it's inside the quotes.  this is incorrect behavior. 
"""
import os, warnings, logging, json, csv
import typing
from sqlmodel import Session
from ewxpwsdb.db.models import WeatherStation

# 
def read_station_table(tsv_file_path:str)->list[dict[str, typing.Any]] | None:
    """read CSV in standard station config format, and flatten into dict useable by station configs. 
    this method does not create stations, only formats a config file for use by package or testing
    Note this does not attempt to validate the data, it is a generic TSV file reader.  

    Args:
        tsv_file_path: path to file in TSV format. Must be tab separated due to bug in dictreader
        
    returns: list of dictionary with fields from TSV file.  
    """

    weatherstation_data = []
    try:
        if not os.path.exists(tsv_file_path): 
            warnings.warn(Warning("File not found {}".format(tsv_file_path)))
            return None
        
        header = False
        # fieldnames = ['station_code','station_type','install_date','timezone','ewx_user_id','lat','lon','location_descriptoin','api_config']
        with open(tsv_file_path, "r") as csvfile:
            # read as dicts, assumes first row is header row
            csvdictreader = csv.DictReader(csvfile, quotechar="'", delimiter='\t')
            if header:
                next(csvdictreader)

            for row in csvdictreader:
                weatherstation_data.append(row)


    except TypeError as e:
        logging.error("TypeError: Exception encountered reading in ewx_pws.py.stations_from_file {}:\n {}".format(tsv_file_path, e))
        raise e
    
    return(weatherstation_data)


def import_station_records(weatherstation_data:list, engine):
    """Given records, inserts rows into station table eg for populating a new DB.  Records must have a station_type that is 
    also alrady in the table 'stationtype' due to foreign key constraints

    Args:
        weatherstation_data (list): list of dictionary eg. from csvdictreader with columns matching WeatherStation Model. 
        engine (Engine, optional):  SQLAlchemy/SQLModel Engine from create_engine().  Defaults to global engine created in database.py
    """

    # uses the global var 'engine' imported above
    with Session(engine) as session:
        # will fail if any one of these records has a problem
        for s in weatherstation_data:
            station_record = WeatherStation.model_validate(s)
            #can put try-except here for IntegrityError
            session.add(station_record)

        # actually insert data, will fail if there are duplicate records
        session.commit()
        session.close()
        return True


def import_station_types(engine):
    """Insert the station types from API modules, for populating a new DB. 

    Args:
        engine (Engine, optional):  SQLAlchemy/SQLModel Engine from create_engine().  Defaults to global engine created in database.py
    """

    from ewxpwsdb.db.models import StationType
    from ewxpwsdb.weather_apis import STATION_TYPE_LIST

    station_type_objects = [StationType(station_type=station_type ) for station_type in STATION_TYPE_LIST]
    
    with Session(engine) as session:
        #crash here
        session.bulk_save_objects(station_type_objects)
        session.commit()
        session.close()


def import_station_file(tsv_file:str, engine):
    """Reads TSV file and inserts all rows as station records for populating a new DB. 

    Args:
        tsv_file (str): path to a TSV file with station data.  See read_station_table() above for details
        engine (Engine, optional):  SQLAlchemy/SQLModel Engine from create_engine().  Defaults to global engine created in database.py
    """
    
    station_list = read_station_table(tsv_file)
    if station_list:
        return(import_station_records(station_list, engine))
    else:
        # no stations to import
        return False
    

    
        


        
