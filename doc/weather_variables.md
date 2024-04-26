# Weather Variables and their summary

### Enviroweather Personal Weather Station  Project

The following are variables stored for weather stations.  These are named and designed to match the datbase used by Enviroweather (MAWN db).   These variables are created by reading and transforming value found in the content of the response from the API from the various weather station cloud vendors, not from the station itself.   

| **weather variable** | **sensor description**   | **units**  | **hourly summary**   | **daily summary**     | **notes** |
|---                   |---                       |---         |---                   |---                    |---        |
| **atemp**   | air temperature    | centigrade     | mean  | mean, min, max    |   |
| **pcpn**    | precipitation      | mm             | sum   | sum               |   |
| **relh**    | relative humidity  | percent        | mean  | mean              |   |
| **lws0**    | leaf weatness, wet (1) or not (0) for the time period        | unitless | percent time wet (sum/count) | percent time wet  | do we need to keep the zero in PWS if we are only ever going to have one value? e.g. just make this "lws" because it's the only one that has a zero for PWS so far |
| **wspd**    | wind speed         | kph?           | mean?  | ? mean, min, max? |   |
| **wdir**    | wind direction     | degrees from N |   |   |  |
| **srad**   | solar radiation    |                |   |   |   |
| **dwpt**    | dew point          |                |   |   |   |
| **rpet**    | Reference Potential Evapotranspiration  |   |   |   |   |
| **smst**    | soil moisture      |   |  |  |  |
| **stmp**    | soil temperature, at depth ? cm  |  C  | avg  | avg | 
