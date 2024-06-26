# Enviroweather Personal Weather Station (PWS) API output variable definitions

## Background

PWS stores data differently than MAWN and hence calculates data differently.   The system collects and stores data on 5, 15, or 30 
minute intervals depending on the station type and then calculates these summary statistcs for those for each station.  The 
Campbell stations that MAWN uses reports hourly and daily values from their loggers.   

Fields are named for clarity, for example some station types have a Maximum temperature output, so max temp is 
labelled "max of the max" but those that don't use  so the max of of the average air temp

Not all fields have equivalant MAWN fields as they may not be necessary for MAWN such as counts of records since 
different stations have different sampling intervals and 

## WeatherStation

| Station Variable |  Example data | Description | Comparable MAWN Variable | Comment |
| ---              | ---           | ---         | ---                      | --- | 
| station_type     |  SPECTRUM     | unique station code | Table name       | MAWN stores station data in separate tables    |
| install_date |  2023-05-01  |   |  |  |
| timezone |  US/Eastern  | timezone of this station, in IANA standard format | NA | all MAWN stations are US/Eastern  |
| ewx_user_id |  0  | the EWX db user idthat claims this personal weather station | NA  |  |
| lat |  42.70736  | latitude decimal degrees | ? | this is as reported by user but not verified to be current |
| lon |  84.46512  | longitude decimal degrees | ? | this is as reported by user but not verified to be current |
| location_description |  EWX Field Office  |  description of location | ? |  |
| background_place |  MSU  | which EWX station is equivalent  |  |  |
| api_config |  JSON dictionary  | connection secrets for this stations vendor API | NA | these are hidden from API and Printing, used internally |
| sampling_interval |  5  | frequency of data reported, minutes | NA  |  |
| expected_readings_day |  288  | given frequency, how many samples are expected | NA | used to determine percent valid readings / day |
| expected_readings_hour |  12  | given frequency, how many samples are expected | NA |  used to determine percent valid readings / hour |
| first_reading_datetime |  2024-03-31T20:00:00  | timestamp of first record in 'reading' table, station local timezone | NA |  |
| first_reading_datetime_utc |  2024-04-01T00:00:00Z  |  timestamp of first record in 'reading' table, UTC | NA |  |
| latest_reading_datetime |  2024-06-26T09:30:00  | timestamp of latest record in 'reading' table, station local timezone | NA |  |
| latest_reading_datetime_utc |  2024-06-26T13:30:00Z   |  timestamp of latest record in 'reading' table, UTC   | NA |  |
| supported_variables |  `[\"atmp\",  \"lws\",  \"pcpn\",  \"relh\",  \"srad\", \"wspd\",  \"wdir\",  \"wspd_max\"]`   | JSON list of variables this station reports | NA | needed since all readings are in the same table and NULL may mean either not supported or invalid or not reported |


##  Hourly summary data

*from "HourlySummary" class in module models/summary_models.py*

| PWS Hourly variable| PWS Example Hourly Data| Description| comparable EWX Hourly field | comments |
| --- | --- | --- | --- | --- | 
| station_code| EWXSPECTRUM01| unique station identifier| name of table|  | 
| year| 2024| year of reading| year|  | 
| day| 177| day of the year of reading| day|  | 
| represented_date| 2024-06-25| date of the reading for the station's timezone| date|  | 
| represented_hour| 1| hour number (00:00-00:59 is hour 1) in station time zone | ? | not sure is MAWN 'hour' is the same | 
| record_count| 12| number of records included in these statistics used to determine percent valid values are available | NA|  | 
| atmp_count| 12| number of non-null and validated atmp values| NA|  | 
| atmp_avg_hourly| 20.22| mean hourly air temp, C | atmp|  | 
| atmp_max_hourly| 20.72| max of mean hourly air temp, C | NA|  | 
| atmp_min_hourly| 19.56| min of mean hourly air temp, C | NA|  | 
| atmp_max_max_hourly| null| max of max hourly air temp, if atmp_max is available, C | NA|  | 
| atmp_min_min_hourly| null| min of min hourly air temp, if atmp_min is available, C | NA|  | 
| relh_avg_hourly| 77.9| average of relh value, percent | relh|  | 
| pcpn_count| 12| number of non-null and validated pcpn values| NA|  | 
| pcpn_total_hourly| 0| hourly sum of precipitation, mm | pcpn |  | 
| lws_count| 12| number of non-null and validated ws values| NA|  | 
| lws_wet_hourly| 0| number of lws value > 1 for this hour| NA |  | 
| lws_pwet_hourly| 0| hourly percent of lws values > 1| lws0_pwet |  | 
| wdir_avg_hourly| 273| hourly average wind direction in degrees inlcuding zeros| wdir | 0 often indicates calm, not actual direction | 
| wdir_sdv_hourly| 0| hourly std deviation (population) wind dir, including zeros| wstdv | 0 often indicates calm, not actual direction  | 
| wdir_null_avg_hourly| 273| hourly average wind direction degrees, not including zeros | wdir | excludes calm readings | 
| wdir_null_sdv_hourly| 0| hourly standard deviation (population) wind direction, not including zeros | wstdv | excludes calm readings |
| wspd_avg_hourly| 0.3| hourly average wind speed m/s  |wspd |  | 
| wspd_max_hourly| 1.34| hourly max wind speed, m/s | wspd_max | some stations have max wind speed option but not all   | 


### Example MAWN DB station Hourly table:

```
'year' INTEGER NOT NULL,
'day' INTEGER NOT NULL,
'hour' INTEGER NOT NULL,
rpt_time INTEGER NOT NULL,
'date' DATE NOT NULL,
'time' TIME WITHOUT TIME ZONE NOT NULL,
atmp REAL,
relh REAL,
soil0 REAL,
soil1 REAL,
mstr0 REAL,
mstr1 REAL,
srad REAL,
wdir REAL,
wspd REAL,
wstdv REAL,
wspd_max REAL,
wspd_maxt INTEGER,
pcpn REAL,
lws0_pwet REAL,
lws1_pwet REAL,
rpet REAL,
volt REAL,
id BIGINT NOT NULL
```

## Daily Summary Variables

*from "HourlySummary" class in module models/summary_models.py*


