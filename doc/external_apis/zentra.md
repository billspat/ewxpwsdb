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

   - Full information about the ZENTRA Cloud API can be found at https://zentracloud.com/api/v3/documentation/. This site includes all available API calls, their correct use and formatting.

### Python Binding

- Required Parameters

| Name           | Contents                                                     | Type     |
| -------------- | ------------------------------------------------------------ | -------- |
| sn             | Serial number of device (device_sn)                          | str      |
| token          | API Key (Client-specific value)                              | str      |
| start_datetime | Start date and time (UTC time zone expected)                 | datetime |
| end_datetime   | End date and time (UTC time zone expected)                   | datetime |
| tz             | Time zone information of the station (options: 'HT', 'AT', 'PT', 'MT', 'CT', 'ET') | str      |

> NOTE: start_datetime & end_datetime must be in UTC time zone for Python binding to correctly interpret date and time

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
    'token': API_KEY,
    'start_datetime': start_date_utc,
    'end_datetime': end_date_utc,
    'tz' : 'ET'
}
zparams = ZentraParam(**params)
zreadings = ZentraReadings(zparams)
print(zreadings.response) # print raw JSON response
print(zreadings.transformed_resp) # print transformed response in list of dict format
```

### Data Transformation

-  Zentra stations may be set to utilize metric system thus no further conversion methods were necessary
- Measurement mapping

| Zentra Measurement Variable | Backend DB Variable |
| :-------------------------: | :-----------------: |
|       Air Temperature       |        atemp        |
|        Precipitation        |        pcpn         |
|      Relative Humidity      |        relh         |

> NOTE: To make the timestamp format equal to other station vendors, we removed the time zone notation in the back (e.g., "2022-06-07 15:10:00-04:00" --> "2022-06-07 15:10:00")

### Sample Data Output

Sample RAW JSON API response and the transformed response outputs may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Sample%20Weather%20Data%20Output?csf=1&web=1&e=55ky0M).

### Special Consideration

Zentra API has built in API call rate limiter that rejects any subsequent API call request within 1-min. In order to avoid getting this in our operation, we implemented bypassing routine in our Python binding.

```python
# Send the request and get the JSON response
while True:
  resp = Session().send(self.request)
  if resp.status_code != 429:
    break
  print("message: {}".format(resp.text))
  sleep(60)
```

By encapsulating with infinite `while` loop, Python binding will make initial call and then if the returned HTTP status code is ***anything other than*** `429` 'Too Many Requests', it quits the `while` loop and execute subsequent methods to completion; however, if the response do indeed get `429` code, it will print the message and ***wait 60 seconds*** before submitting same request again. 

