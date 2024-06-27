# Spectrum Weather Stations

## Sensors/Tranforms

Spectrum [Leaf Wetness sensor overview information from their website](https://www.specmeters.com/weather-monitoring/sensors-and-accessories/sensors/environmental-sensors/leaf-wetness-sensor/)

> "Grid-like, resistance-type sensor mimics moisture on vegetation from 0 (dry) to 15 (wet)."

[Per the manual (PDF)](https://www.specmeters.com/assets/1/22/Product_Manual_-_Leaf_Wetness_(Item__3666).pdf)

> "The sensor reads wetness by measuring the resistance on the grid. The resistance measurement is converted to a Leaf Wetness value from 0-15, in whole numbers. Any value over 6 is con- sidered ‘wet’."


### Authentication

Spectrum weather station API requires an ***API Key*** that is a customer-specific token, for authenticating API requests.

> NOTE: It should be of the form `customerApiKey=<API_KEY>` as a query parameter.


### Endpoint in Action

1. Get the 50 most recent sensor data records for a specific customer device

   - In order to get readings for a given device, following request/call needs to be made:

   | Component | Contents                                              |
   | --------- | ----------------------------------------------------- |
   | Header    | Accept: application/json                              |
   | Method    | GET                                                   |
   | URL       | https://api.specconnect.net:6703/api/Customer/GetData |

   - Parameters

   | Name           | Description                                                  | Data Type | Parameter Type | Required |
   | -------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | customerApiKey | Customer API Key                                             | str       | Query          | Y        |
   | serialNumber   | Device Serial Number                                         | str       | Query          | Y        |
   | optValues      | Additional (comma-separated) calculated values (vpd, dewPoint, wetBulb, deltaT, heatIndex, absoluteHumidity) | str       | Query          | N        |
   | optUnits       | Comma-separated list of unit preferences for temperature, rainfall, pressure, (wind-)speed and compaction sensors | str       | Query          | N        |

2. Get sensor data for a specific customer device for a specific date/time range

   - In order to get readings for a given device over a specified time period, following request/call needs to be made:

   | Component | Contents                                                     |
   | --------- | ------------------------------------------------------------ |
   | Header    | Accept: application/json                                     |
   | Method    | GET                                                          |
   | URL       | https://api.specconnect.net:6703/api/Customer/GetDataInDateTimeRange |

   - Parameters

   | Name           | Description                                                  | Data Type | Parameter Type | Required |
   | -------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | customerApiKey | Customer API Key                                             | str       | Query          | Y        |
   | serialNumber   | Device Serial Number                                         | str       | Query          | Y        |
   | startDate      | Start of Date Range (e.g., 2021-08-01 00:00)                 | datetime  | Query          | Y        |
   | endDate        | End of Date Range (e.g., 2021-08-31 23:59)                   | datetime  | Query          | Y        |
   | optValues      | Additional (comma-separated) calculated values (vpd, dewPoint, wetBulb, deltaT, heatIndex, absoluteHumidity) | str       | Query          | N        |
   | optUnits       | Comma-separated list of unit preferences for temperature, rainfall, pressure, (wind-)speed and compaction sensors | str       | Query          | N        |


> NOTE: Spectrum API expects local time (zone) of the station's location for its `startDate` and `endDate`

1. Get sensor data for a specific customer device for a specific date

   - In order to get readings for a given device over a specified date, following request/call needs to be made:

   | Component | Contents                                                    |
   | --------- | ----------------------------------------------------------- |
   | Header    | Accept: application/json                                    |
   | Method    | GET                                                         |
   | URL       | https://api.specconnect.net:6703/api/Customer/GetDataByDate |

      - Parameters

   | Name           | Description                                                  | Data Type | Parameter Type | Required |
   | -------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | customerApiKey | Customer API Key                                             | str       | Query          | Y        |
   | serialNumber   | Device Serial Number                                         | str       | Query          | Y        |
   | date           | Date (e.g., 2021-08-01)                                      | datetime  | Query          | Y        |
   | optValues      | Additional (comma-separated) calculated values (vpd, dewPoint, wetBulb, deltaT, heatIndex, absoluteHumidity) | str       | Query          | N        |
   | optUnits       | Comma-separated list of unit preferences for temperature, rainfall, pressure, (wind-)speed and compaction sensors | str       | Query          | N        |

2. Get a specific number of recent sensor data records for a specific customer device

   - In order to get a specific number of readings for a given device, following request/call needs to be made:

   | Component | Contents                                                     |
   | --------- | ------------------------------------------------------------ |
   | Header    | Accept: application/json                                     |
   | Method    | GET                                                          |
   | URL       | https://api.specconnect.net:6703/api/Customer/GetDataByRange |

   - Parameters

   | Name           | Description                                                  | Data Type | Parameter Type | Required |
   | -------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | customerApiKey | Customer API Key                                             | str       | Query          | Y        |
   | serialNumber   | Device Serial Number                                         | str       | Query          | Y        |
   | count          | The number of recent records to retrieve                     | int       | Query          | Y        |
   | optValues      | Additional (comma-separated) calculated values (vpd, dewPoint, wetBulb, deltaT, heatIndex, absoluteHumidity) | str       | Query          | N        |
   | optUnits       | Comma-separated list of unit preferences for temperature, rainfall, pressure, (wind-)speed and compaction sensors | str       | Query          | N        |

3. Addtional Endpoint information

   - Full information about the SpecConnect Customer API can be found at https://api.specconnect.net:6703/Help/. This site includes all available API calls, their correct use and formatting.

### Variable mapping

- Required Parameters

| Name           | Contents                                                     | Type     |
| -------------- | ------------------------------------------------------------ | -------- |
| sn             | Device Serial Number (serialNumber)                          | str      |
| apikey         | API Key (customerApiKey)                                     | str      |
| start_datetime | Start date and time (UTC time zone expected)                 | datetime |
| end_datetime   | End date and time (UTC time zone expected)                   | datetime |
| tz             | Time zone information of the station (options: 'HT', 'AT', 'PT', 'MT', 'CT', 'ET') | str      |

> NOTE: start_datetime & end_datetime must be in UTC time zone for Variable mapping to correctly interpret date and time

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
    'sn': DEVICE_SN,
    'apikey': API_KEY,
    'start_datetime': start_date_utc,
    'end_datetime': end_date_utc,
    'tz' : 'ET'
}
sparams = SpectrumParam(**params)
sreadings = SpectrumReadings(sparams)
print(sreadings.response) # print raw JSON response
print(sreadings.transformed_resp) # print transformed response in list of dict format
```

### Data Transformation

- Spectrum stations utilizes imperial system thus unit conversion is applied to transformed response:
  -  `F` (Fahrenheit) to `C` (Celsius)  
  - `in` (Inch) to `mm` (millimeter)
- Measurement mapping

| Spectrum Measurement Variable | Backend DB Variable |
| :---------------------------: | :-----------------: |
|          Temperature          |        atmp        |
|           Rainfall            |        pcpn         |
|       Relative Humidity       |        relh         |

###  Sample Data Output

Sample RAW JSON API response and the transformed response outputs may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Sample%20Weather%20Data%20Output?csf=1&web=1&e=8X3bp3). 

### Special Consideration

For unknown reason, Spectrum API does ***NOT*** seem to handle Python `datetime` object correctly, if it has time zone information baked in the Python `datetime` object.

For example, `2022-06-02 15:30:22.946254-04:00` this datetime object will cause Spectrum API to incorrectly interpret date/time and cause API to return strange time span result or no result at all. Therefore, using below:

```python
start_datetime.replace(tzinfo=None)
```

we change from `2022-06-02 15:30:22.946254-04:00` to `2022-06-02 15:30:22.946254`. This bypasses werid limitation in Spectrum API.