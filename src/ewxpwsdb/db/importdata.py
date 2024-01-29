"""Utilites to import data for the database. 
The import datafile _must_ be tab delimited
 Note that in Python 3.11, the dict reader seems to be broken.  
If using single quotes as a quote character, the reader _still_ splits the line on commas even if it's inside the quotes.  this is incorrect behavior. 
"""
import os, warnings, logging, json, csv
from ewxpwsdb.db.models import WeatherStation

# globals 
from ewxpwsdb.db.database import engine, Session

def read_station_table(tsv_file_path:str)->dict:
    """read CSV in standard station config format, and flatten into dict useable by station configs. 
    this method does not create stations, only formats a config file for use by package or testing
    csv_file_path: path to CSV file
    returns: list configs
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


def import_station_records(weatherstation_data:list):
    """ this has side effect of insert records into the database"""
    # uses the global var 'engine' imported above
    with Session(engine) as session:
        # will fail if any one of these records has a problem
        for s in weatherstation_data:
            station_record = WeatherStation.model_validate(s)
            session.add(station_record)

        # actually insert data, will fail if there are duplicate records
        session.commit()

def import_station_table(tsv_file:str):
    """add all records from the station tsv file into the database"""
    # uses the global var 'engine' imported above
    station_list = read_station_table(tsv_file)
    import_station_records(station_list)
    
        


        
