# Onset Weather Stations

## <span style="color:red">Onset now uses the LICOR api type, api.licor.cloud</span>

### Authentication

Onset weather station API requires ***client_id*** and ***client_secret*** that are assigned by Onset and use those to generate ***bearer token***.

To create, following request/call needs to be made:

| Component | Contents                                                     |
| --------- | ------------------------------------------------------------ |
| Header    | Accept: application/json, Content-Type: application/x-www-form-urlencoded |
| Method    | POST                                                         |
| URL       | https://webservice.hobolink.com/ws/auth/token                |
| Data      | "grant_type" : "client_credentials", "client_id" : "CLIENT_ID", "client_secret" : "CLIENT_SECRET" |

> NOTE: `client_id` and `client_secret` is **different** from the login credentials for hobolink.com

### Endpoint in Action

1. Get data via File Endpoint

   - In order to collect measurement data from a station over a specified time period, following request/call needs to be made:

   | Component | Contents                                                     |
   | --------- | ------------------------------------------------------------ |
   | Header    | Accept: application/json, Authorization: Bearer ACCESS_TOKEN |
   | Method    | GET                                                          |
   | URL       | https://webservice.hobolink.com/ws/data/file/{format}/user/{userId} |

   - Parameters

   | Name            | Description                                                  | Data Type | Parameter Type | Required |
   | --------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | format          | The format data should be returned in. (Only JSON is supported) | str       | Path           | Y        |
   | userId          | Numeric ID of the user account                               | str       | Path           | Y        |
   | loggers         | Comma-delimited list of logger serial numbers that data should be grabbed for. List is limited to 10 different loggers at a time | str       | Query          | Y        |
   | start_date_time | The date furthest in the past data should be grabbed for. Should be in the format yyyy-MM-dd HH:mm:ss in **UTC time zone** | str       | Query          | Y        |
   | end_date_time   | This is only needed if time frame querying is desired (see later section). Should be in the format yyyy-MM-dd HH:mm:ss in **UTC time zone** | str       | Query          | Y        |
   
   > NOTE: userId may be pulled from the HOBOlink URL: www.hobolink.com/users/<userId>
   
   > NOTE: As written in above table, Onset/Hobo API expects UTC time (zone) for its `start_date_time` and `end_date_time`.
   
4. Addtional Endpoint information

   - Full information about the Onset API can be found at https://webservice.hobolink.com/ws/data/info/index.html. This site includes all available API calls, their correct use and formatting.

### Variable mapping

- Required Parameters

| Name           | Contents                                                     | Type     |
| -------------- | ------------------------------------------------------------ | -------- |
| sn             | Logger serial number that data should be grabbed for         | str      |
| client_id      | client-specific value provided by Onset                      | str      |
| client_secret  | client-specific value provided by Onset                      | str      |
| ret_form       | The format data should be returned in. (Only JSON is supported) | str      |
| user_id        | Numeric ID of the user account                               | str      |
| start_datetime | Start date and time (UTC time zone expected)                 | datetime |
| end_datetime   | End date and time (UTC time zone expected)                   | datetime |
| tz             | Time zone information of the station (options: 'HT', 'AT', 'PT', 'MT', 'CT', 'ET') | str      |
| sensor_sn      | key & value pairs of sensor serial numbers for measurements that would be included in transformed response (e.g., {'atmp': '123456-7', ... , 'pcpn': '129876-2'}) | dict     |

> NOTE: start_date & end_date must be in UTC time zone for Variable mapping to correctly interpret date/time

> NOTE: HT: Hawaii Time / AT: Alaska Time / PT: Pacific Time / MT: Mountain Time / CT: Central Time / ET: Eastern Time

- Usage

```python
local = pytz.timezone('US/Eastern')
start_date = datetime.strptime('11-19-2021 14:00', '%m-%d-%Y %H:%M')
end_date = datetime.strptime('11-19-2021 16:00', '%m-%d-%Y %H:%M')
start_date_local = local.localize(start_date)
end_date_local = local.localize(end_date)
start_date_utc = start_date_local.astimezone(pytz.utc)
end_date_utc = end_date_local.astimezone(pytz.utc)

params = {
    'sn': SERIAL_NO,
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
    'ret_form': 'JSON',
  	'user_id': USER_ID
    'start_datetime': start_date_utc,
    'end_datetime': end_date_utc,
    'tz': 'ET'
    'sensor_sn': {'atmp': TEMP_Sensor_SN, 'pcpn': PRECP_Sensor_SN, 'relh': RELHUM_Sensor_SN}
}
oparams = OnsetParam(**params)
oreadings = OnsetReadings(oparams)
print(oreadings.response) # print raw JSON response
print(oreadings.transformed_resp) # print transformed response in list of dict format
```

### Data Transformation

- Onset/Hobo station reports measurements in both emperial and metric systems; thus, no further conversion methods were necessary.
- Measurement mapping

|        Onset/Hobo Measurement Variable         | Backend DB Variable |
| :--------------------------------------------: | :-----------------: |
|    [Temperature Sensor SN] --> ['si_value']    |        atmp        |
|   [Precipitation Sensor SN] --> ['si_value']   |        pcpn         |
| [Relative Humidity Sensor SN] --> ['us_value'] |        relh         |

> NOTE: `si_value` records readings in metric system whereas `us_value` records readings in imperial system

###  Sample Data Output

Sample RAW JSON API response and the transformed response outputs may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Sample%20Weather%20Data%20Output?csf=1&web=1&e=8X3bp3). 

### Special Consideration

Onset/Hobo station API response does have notation named `sensor_measurement_type`; however, it is not always clear what sensor is what we are interested for transformed response.

For example, below is a sample RAW JSON response snippet:

```JSON
{
      "logger_sn": "21092695",
      "sensor_sn": "21079936-1",
      "timestamp": "2022-04-12 09:05:00Z",
      "data_type_id": "1",
      "si_value": 0.7423559914496991,
      "si_unit": "\u00b0C",
      "us_value": 33.33624078460946,
      "us_unit": "\u00b0F",
      "scaled_value": 0.0,
      "scaled_unit": null,
      "sensor_key": 1167328,
      "sensor_measurement_type": "Temperature"
    }

...snip...

{
      "logger_sn": "21092695",
      "sensor_sn": "21215409-4",
      "timestamp": "2022-04-12 09:05:00Z",
      "data_type_id": "1",
      "si_value": 6.300000190734863,
      "si_unit": "\u00b0C",
      "us_value": 43.34000034332276,
      "us_unit": "\u00b0F",
      "scaled_value": 0.0,
      "scaled_unit": null,
      "sensor_key": 1167341,
      "sensor_measurement_type": "Temperature"
    },
    {
      "logger_sn": "21092695",
      "sensor_sn": "21215409-5",
      "timestamp": "2022-04-12 09:05:00Z",
      "data_type_id": "1",
      "si_value": 6.5,
      "si_unit": "\u00b0C",
      "us_value": 43.7,
      "us_unit": "\u00b0F",
      "scaled_value": 0.0,
      "scaled_unit": null,
      "sensor_key": 1167337,
      "sensor_measurement_type": "Temperature"
    },
```

As seen here, it's not clear what sensor reading is the `air temperature` that we are looking for.

Logging into the HOBOLink portal, we were able to grab sensor serial number of the `air temperature` sensor as shown below:

![screenshot-hobolink-withsensors](/uploads/4217b404281e9000db2a98d7bc5be857/screenshot-hobolink-withsensors.jpg)

Based on these information, we added a Python `dict` of sensor serial numbers and the fields they represent to the Onset parameters. `Usage` example above illustrates the sample `sensor_sn` Python `dict` type parameter.