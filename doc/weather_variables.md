# Enviroweather Personal Weather Station Project: <br>Weather Variables and their summary

The following are variables stored for weather stations.  These are named and designed to match the datbase used by Enviroweather (MAWN db).   These variables are created by reading and transforming value found in the content of the response from the API from the various weather station cloud vendors, not from the station itself.   

| **variable** | **sensor description**            | **units**    | **hourly summary**      | **daily summary**     | **notes** |
|---           |---                                |---           |---                      |---                    |---        |
| **atmp**     | air temperature                   | C            | mean                    | mean, min, max        |     |
| **dwpt**     | dew point                         | C            | min                     | min?                  |     |
| **lws**      | leaf weatness, wet (1) or not (0) | unitless     | % time wet (sum/count)  | percent time wet      | *   |
| **pcpn**     | precipitation                     | mm           | sum                     | sum                   |     |
| **relh**     | relative humidity                 | percent      | mean                    | mean                  |     |
| **rpet**     | Ref Potential Evapotranspiration  | ?            | ?                       | ?                     |     |
| **smst**     | soil moisture                     | ?            | avg                     | avg                   |  ** | 
| **stmp**     | soil temperature, at depth 4 in   | C            | avg                     | avg                   |  ** | 
| **srad**     | solar radiation                   | ?            | ?                       | ?                     |     |
| **wdir**     | wind direction                    | deg from N   | ?                       | ?                     |     |
| **wspd**     | wind speed                        | kph?         | max                     | mean, min, max?       |     |


### Notes

\* This field (and others) in MAWN/Enviroweather DB are suffixed with 0 to allow for multiple sensors (e.g. sensor 0, sensor 1, etc) but for PWS we only take 1 var for consistency, so there is no numeric subset to any var. 

** MAWN includes the depth in cm in the field names for soil measurements for multiple sensors.  If PWS will have any soil sensors, will there be one standard depth?


### Other variables

MAWN db has different field names for hourly and daily summaries, for example, `wspd` is `wspd_max` for hourly and daily and if PWS also generates new field names for hourly/daily summaries those should be noted here.    

