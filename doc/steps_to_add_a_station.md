## Enviroweather PWS 

# Adding a weather station June 2025

Currently the main way to add a new station is to insert a new row into the 
database `weather_station` table.  This requires using a client program that 
can work with Postgresql.  We use `pgadmin` but several others will work. 

## 1. If you don't have an existing database connection

 - get credentials for the current database. Those are stored with the PWS
 documentation in word document on our private sharepoint.   If you have access
 to the server running PWS, a connection string with db host, user and pw is 
 in the private configuration file used by the PWS program, stored as `.env` 
 in the program folder (typically
 `$HOME/ewxpwsdb/.env`) in the variable `EWXPWSDB_URL`

 - get connected to the database 


## 2. Server Security

The database is hosted on AWS protected by a firewall and the IP address needs 
to be added to that.   See the word document describing the deployment details 
but there is a security group for this project and your IP address needs to be 
added to that security group for postgresql.   See the 
[AWS documentation](https` ://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.RDSSecurityGroups.html)

edit the security group, add a new rule, select 'Postgresql' as the access type, 
and select 'my ip' - in the description add your netid and the location you are 
access the database from (campus address, home office, mobile hotspot etc)

## 3. Edit the database table

Add a new row in the database talbe, which has the following fields: 

- `id` : (do not enter, automatically filled in ) database id assigned by the database
- `station_code` : short, unique string code to ID this station 
- `station_type` : one of station types, all caps.  see station types below
- `install_date` : date in form YYYY-MM-DD
- `timezone` : IANA Timezone key. The default = 'US/Eastern',  https` ://en.wikipedia.org/wiki/List_of_tz_database_time_zones".  Use a time
- `ewx_user_id` : owner of the station, a valid EWX user ID.  Use 'masonk'
- `lat` : Latitude.  Required but does not have to be exact, use nearby location if you want to obfuscate.  
- `lon` : Longitude. Required but does not have to be exact
- `location_description` : optional detail about where the station is located
- `background_place` : An existing Enviroweather station code, used by RM-API if this station is not available
- `active` : True/False  False means the station is archived and no longer used
- `api_config` : this is a JSON-formatted string with log-in details for the API in question.  See below

###  Station Types

These are actually "API types" but the name was chosen early in the project
and hasn't changed.   Some APIs support multiple station types. 

- 'ZENTRA': Meter Group
- 'ONSET': Old API for HoboLink, no longer used
- 'DAVIS': davis
- 'RAINWISE': old API, no longer used
- 'SPECTRUM': spectrum
- 'LOCOMOS': Ubidots api created by Youngsuk Dong
- 'LICOR': Used for Onset/HOBO link stations

### API Configuration

The field `api_config` must be in json format, which uses double quotes and looks like

`{"key1":"value", "key1":"value"}`  for each key.  Again keys and values must be 
in double quotes.

each API has it's own API configuration fields.   Documentation to follow but in the 
code based, each API script file in [../src/ewxpwsdb/weather_apis](../src/ewxpwsdb/weather_apis) 
has a class `StationAPIConfig()`  for example, `class DavisAPIConfig(WeatherAPIConfig):`

Each config class has a list of configuration settings that must be there, documentation
to follow but the code has the definitive list.   They all have a key "_station_type" which 
you don't need to enter in the database, set automatically by the code. 

For example, Davis API requires the following configuration values: 

```
sn             : str #  The serial number of the device.
apikey         : str # The user's API access key. 
apisec         : str # API security that is used to compute the hash.
```

This would be entered into the database field `api_config` exactly like this 
(these are made-up numbers and not for a real station)

```
{"sn":"117999","apikey":"adlwidjowkdjlsoqw690asjaqw0jsjwo","apisec":"rlsiel89lssljwie9s080spsdps03xd3"}
```

Each API has documentation in the /doc folder for how to access the info and 
enter into the database. 

Due to the limited resources and time it would take to create and maintain forms for each type
of API, we are entering these by hand for now.  

Once the station/API config is added to the DB, you should then collect some recent 
data.   The schedule for collecting data will attempt to get the last 2 weeks of data 
from it.  

### Testing

Once the station is added to the database used by the software, you can test 
using the command line interface (CLI) `ewxpws` by attempting to collect some data. 

Pick a date when the station was active and pull all data for that day.  For 
5-minute stations, this can take a while (10 minutes) as 144 records are retrieved 
and inserted.  

Turn on debugging logging by setting the variable `LOG_LEVEL_CONSOLE=DEBUG`

For example, for a station with unique station code `EWXDAVIS01`, collect data 
from June 30, 2025 and put it into the database.  In the current version the time
is required for the start/end date-times, so just use midnight. 

```
export LOG_LEVEL_CONSOLE=DEBUG
ewxpws collect -s 2025-06-29T00:00:00+00 -e 2025-06-30T00:00:00+00 EWXDAVIS02
```

If the output says "No response from station N for interval..." that means the 
connection configuration is incorrect.   

