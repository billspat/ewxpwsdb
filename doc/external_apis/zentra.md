# Zentra Weather Stations

### Authentication

Zentra weather station API requires an ***API Key*** that is an user token each ZENTRA Cloud user has upon creating an account, for authenticating API requests.

> NOTE: It should be of the form `Token <API_TOKEN>` in the request header.

### Endpoint in Action

1. Get reading

   - In order to get readings for a given device, following request/call needs to be made:

   | Component | Contents                                                   |
   | --------- | ---------------------------------------------------------- |
   | Header    | Accept: application/json, Authorization: Token <API_TOKEN> |
   | Method    | GET                                                        |
   | URL       | https://zentracloud.com/api/v3/get_readings/               |

   - Parameters

   | Name          | Description                                                  | Data Type | Parameter Type | Required |
   | ------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | device_sn     | Serial number of device having data requested                | str       | Query          | Y        |
   | start_date    | Start date of time range (Default: first reading of the device, Overrides start_mrid) | str       | Query          | N        |
   | end_date      | End date of time range (Default: last reading of the device, Overrides end_mrid) | str       | Query          | N        |
   | start_mrid    | Start mrid of mrid range (Default: first mrid reading of the device) | int       | Query          | N        |
   | end_mrid      | End mrid of mrid range (Default: end mrid reading of the device) | int       | Query          | N        |
   | output_format | Data structure of the response content (Default: JSON / Options: json, df, csv) | str       | Query          | N        |
   | page_num      | Page number (Default: 1)                                     | int       | Query          | N        |
   | per_page      | Number of readings per page (Default: 500, Max: 2000)        | int       | Query          | N        |
   | sort_by       | Sort the readings in ascending or descending order (Default: descending) | str       | Query          | N        |
   
   > NOTE: Zentra API expects local time (zone) of the station's location for its `start_date` and `end_date`
   
3. Addtional Endpoint information

   - Full information about the ZENTRA Cloud API can be found at https://zentracloud.com/api/v4/documentation/. This site includes all available API calls, their correct use and formatting.

### Variable mapping

- Required Parameters

| Name           | Contents                                                     | Type     |
| -------------- | ------------------------------------------------------------ | -------- |
| sn             | Serial number of device (device_sn)                          | str      |
| token          | API Key (Client-specific value)                              | str      |
| start_datetime | Start date and time (UTC time zone expected)                 | datetime |
| end_datetime   | End date and time (UTC time zone expected)                   | datetime |
| tz             | Time zone information of the station (options: 'HT', 'AT', 'PT', 'MT', 'CT', 'ET') | str      |

> NOTE: start_datetime & end_datetime must be in UTC time zone for Variable mapping to correctly interpret date and time

> NOTE: HT: Hawaii Time / AT: Alaska Time / PT: Pacific Time / MT: Mountain Time / CT: Central Time / ET: Eastern Time


### Data Transformation

Zentra stations may be set to utilize metric system or english in the cloud 
portal.  Hence you must determine the units currently used in the response
data. 

the Response has an entry for each sensor with metadata and readings, like

```JSON
{
    "Air Temperature": [
        {
            "metadata": {
                "device_name": "z6-12345",
                "device_sn": "z6-12345",
                "port_number": 5,
                "sensor_name": "ATMOS 41",
                "sensor_sn": "x",
                "units": " °C"
            },
            "readings": [
                {}
            ]
```

Notice the units from the API swagger documentation show as " °C" but when loaded
using Python JSON, it appears as ' \\u00b0C'

The timestamp is in local time with timezone "2022-06-07 15:10:00-04:00" 

### Sample Data Output

Sample RAW JSON API response and the transformed response outputs may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Sample%20Weather%20Data%20Output?csf=1&web=1&e=55ky0M).

### Special Considerations

Zentra API has built in API call rate limiter that rejects any subsequent API call request within 1-min, returns a `429` error code (*too many requests**) and shows the number of seconds until the next call can be made.   This package catches that error code and simply waits for the number of seconds and requests data again. 

The Zentra cloud API will return maximum of 2000 weather records per request.  For a station that samples weather every 5 minutes, this translates to just under 7 days of data maximum per request.   If a long time interval is requested (for example, for requesting historical data or data gaps during down time when a station comes on-line), this package splits up that interval and makes multiple API requests.  However due to the rate limiter described above, you will have wait between each request.   

The Zentra Cloud api takes at least 5 minutes from the current time to have weather data ready to request.   If you request a time interval for which there is no data in any portion, it seems to consider this an invalid interval and will return no data.  Hence you can't include the current time in your request.   For the most current data, request a time interval the spans up to at most 5 -10 minutes ago.  
