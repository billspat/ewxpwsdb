# Davis Weather Stations

### Authentication

Davis (WeatherLink) weather station API requires an ***API Key***, an ***API Secret***, a request ***timestamp*** and a calculated ***API Signature*** for authenticating API requests.

- **API Key**

  API Key is a unique ID that identifies the API user making the API call. API Key must be passed as a query parameter in all API request.

  

- **API Secret**

  API Secret is a secret value that is used to calculate a signature for each API request.

  > NOTE: API Secret must be protected and if compromised it wll allow other s to access API while pretending to be the user

  

- **API Request Timestamp**

  API request timestamp is the Unix timestamp at the time the API request is being generated. Every request to the WeatherLink v2 API must use the current Unix timestamp and the API signature must be recomputed to account for the new timestamp on each request.

  > NOTE: The purpose of the timestamp is to prevent request replay attacks.

  

- **API Signature**

  The API Signature process takes all of the request parameters and the API Secret and computes a fingerprint-like value that represents the request. Every request to the WeatherLink v2 API must calculate a new signature for the parameters being sent in the API call. 

  > NOTE: This API Signature is used to prevent API request parameter tampering.

  To calculate the signature use the HMAC SHA-256 algorithm with the concatenated parameter string as the message and the API Secret as the HMAC secret key. The resulting computed HMAC value as a hexadecimal string is the API Signature. Sample of computing API Signature is shown below:

  ```python
      def __compute_signature(self):
          def compute_signature_engine():  # compute_engine
              for key in params:
                  print("Parameter name: \"{}\" has value \"{}\"".format(key, params[key]))
  
              data = ""
              for key in params:
                  data = data + key + str(params[key])
              print("Data string to hash is: \"{}\"".format(data))
  
              sig = hmac.new(
                  self.apisec.encode('utf-8'),
                  data.encode('utf-8'),
                  hashlib.sha256).hexdigest()
              print("API Signature is: \"{}\"".format(sig))
              return sig
  
          if self.start_date and self.end_date:  # if datetime is specified
              temp_list = list()
              for st, ed in self.date_tuple_list:
                  params = {'api-key': self.apikey,
                            'station-id': self.sn,
                            't': self.t,
                            'start-timestamp': st,
                            'end-timestamp': ed}
                  params = collections.OrderedDict(sorted(params.items()))
                  apisig = compute_signature_engine()
                  temp_list.append((st, ed, apisig))
              self.date_tuple_list = temp_list
              for elem in self.date_tuple_list:
                  print(elem)
          else:
              params = {'api-key': self.apikey, 'station-id': self.sn, 't': self.t}
              params = collections.OrderedDict(sorted(params.items()))
              self.apisig = compute_signature_engine()
  ```

### Endpoint in Action

1. Get current data

   - In order to collect current measurement data from a station, following request/call needs to be made:

   | Component | Contents                                             |
   | --------- | ---------------------------------------------------- |
   | Header    | Accept: application/json                             |
   | Method    | GET                                                  |
   | URL       | https://api.weatherlink.com/v2/current/{station-id}/ |

   - Parameters

   | Name          | Description                                | Data Type | Parameter Type | Required |
   | ------------- | ------------------------------------------ | --------- | -------------- | -------- |
   | station-id    | A single station ID                        | str       | Path           | Y        |
   | api-key       | API Key                                    | str       | Query          | Y        |
   | api-signature | API Signature                              | str       | Query          | Y        |
   | t             | Unix timestamp when the query is submitted | int       | Query          | Y        |
   
1. Get historic data 

   - In order to collect measurement data from a station over a specified time period, following request/call needs to be made:

   | Component | Contents                                              |
   | --------- | ----------------------------------------------------- |
   | Header    | Accept: application/json                              |
   | Method    | GET                                                   |
   | URL       | https://api.weatherlink.com/v2/historic/{station-id}/ |

   - Parameters

   | Name            | Description                                                  | Data Type | Parameter Type | Required |
   | --------------- | ------------------------------------------------------------ | --------- | -------------- | -------- |
   | station-id      | A single station ID                                          | str       | Path           | Y        |
   | api-key         | API Key                                                      | str       | Query          | Y        |
   | api-signature   | API Signature                                                | str       | Query          | Y        |
   | t               | Unix timestamp when the query is submitted                   | int       | Query          | Y        |
   | start-timestamp | Unix timestamp marking the beginning of the data requested. Must be earlier than end-timestamp but not more than 24 hours earlier. | int       | Query          | Y        |
   | end-timestamp   | Unix timestamp marking the end of the data requested. Must be later than start-timestamp but not more than 24 hours later. | int       | Query          | Y        |
   
   > NOTE: While API does not allow timestamp range greater than 24 hours, our Variable mapping will automatically break-down into less than 24hr chunks, make separate API calls and then return the combined responses.   
   
3. Addtional Endpoint information

   - Full information about the Davis (WeatherLink) API can be found at https://weatherlink.github.io/v2-api/api-reference. This site includes all available API calls, their correct use and formatting.

### Variable mapping

- Required Parameters

| Name           | Contents                                                     | Type                |
| -------------- | ------------------------------------------------------------ | ------------------- |
| sn             | Station ID                                                   | str                 |
| apikey         | Client-specific value                                        | str                 |
| apisec         | Client-specific value                                        | str                 |
| start_datetime | Start date and time (UTC expected)                           | datetime (optional) |
| end_datetime   | End date and time (UTC expected)                             | datetime (optional) |
| tz             | Time zone information of the station (options: 'HT', 'AT', 'PT', 'MT', 'CT', 'ET') | str                 |

> NOTE: For date and time range to correctly work, both `start_datetime` and `end_datetime` parameters should be in UTC time zone

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
    'sn': STATION_ID,
    'apikey': API_KEY,
    'apisec': API_SECURITY,
    'start_datetime': start_date_utc,
    'end_datetime': end_date_utc,
    'tz': 'ET'
}
dparams = DavisParam(**params)
dreadings = DavisReadings(dparams)
print(dreadings.response) # print raw JSON response
print(dreadings.transformed_resp) # print transformed response in list of dict format
```

### Data Transformation

-  Precipitation is recorded both in `inch` as well as `millimeter`; thus, no transformation is needed 
-  Temperature is recorded in imperial system only; thus unit conversion is applied to transformed response:
   -  `F` (Fahrenheit) to `C` (Celsius)

-  Measurement mapping

| Davis Measurement Variable | Backend DB Variable |
| :------------------------: | :-----------------: |
|          temp_out          |        atmp        |
|        rainfall_mm         |        pcpn         |
|          hum_out           |        relh         |

### Sample Data Output

Sample RAW JSON API response and the transformed response outputs may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Sample%20Weather%20Data%20Output?csf=1&web=1&e=55ky0M).

### Special Consideration

- 24hr+ Data Polling

  Goal is to overcome Davis weation station API design limitation of only allowing up to 24hrs of data. Our Variable mapping detects time span, breakdown into `<`24hr datetime chunks, makes API calls for each datetime chunk, returns combined JSON responses.

  1. As API parameters are passed using `DavisParam` class, date/time range is calculated and split into 23:59:59 chunks then stored as a tuple in a list
     - [ (st_date1, ed_date1), (st_date2, ed_date2), ... ]

  2. Format time routine iterates the datetime tuple list and add explicit time zone (UTC) information to both start_datetime and end_datetime then convert into Unix Epoch time
  3. API signature (authentication purposes) is computed for each start_datetime and end_datetime pair and stored as three-element tuple
     - [ (st_date1, ed_date1, apisig1), (st_date2, ed_date2, apisig2), ... ]
  4. `DavisReading` class takes the `DavisParam` class and builds Request object for each `start_datetime`, `end_datetime` and `API_signature` tuple
  5. API call is made ***sequentially***, and each JSON response is serialized and appended to a list
