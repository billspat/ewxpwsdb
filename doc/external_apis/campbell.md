# Campbell Weather Stations

### Authentication

Campbell weather station API requires actual ***username*** and ***password*** that end-users use to login to their web portal and use those to generate ***bearer token***.

To create, following request/call needs to be made:

| Component | Contents                                                     |
| --------- | ------------------------------------------------------------ |
| Header    | Content-Type: application/json                               |
| Method    | POST                                                         |
| URL       | https://api.campbellcloud.io/v3/campbell-cloud/tokens        |
| Data/JSON | "grant_type" : "password", "credentials" : { "username" : "*user*" , "password" : "*user_password*"} |

> NOTE: username and password is same as the login credentials for Campbell-Cloud Web-portal

### Endpoint in Action

1. Find user details

   - In order to collect measurement data, we need Campbell Cloud user ID, as well as the organization ID to which the user belongs. To receive the user details, following request/call needs to be made:

   | Component | Contents                                         |
   | --------- | ------------------------------------------------ |
   | Header    | Authorization: Bearer ACCESS_TOKEN               |
   | Method    | GET                                              |
   | URL       | https://api.campbellcloud.io/api_v2/user/session |

   - Within the user details, the value for `kc_id` is the user ID and the value for `organization_id` is the organization ID.

   - Sample output [JSON File](https://michiganstate.sharepoint.com/sites/Geography-EnviroweatherTeam/_layouts/15/download.aspx?UniqueId=a2ac6667c61f4f52934aa5cb90a9b730&e=rLQ6RJ) may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Campbell_Info_JSONs?csf=1&web=1&e=YC4hxN).
   
     > NOTE: Campbell Cloud user ID is not the username used to login to Campbell-Cloud web-portal
   
2. Find station IDs

   - Station IDs are required when making measurement calls. To receive the station list, following request/call needs to be made:

   | Component      | Contents                                                     |
   | -------------- | ------------------------------------------------------------ |
   | Header         | Authorization: Bearer ACCESS_TOKEN                           |
   | Method         | GET                                                          |
   | URL            | https://api.campbellcloud.io/v3/campbell-cloud/organizations/{organization_id}/resources/{user_id}/stations?brief=true |
   | Path Parameter | {organization_id} - `organization_id` from the user details, {user_id} - `kc_id` from the user details |
   
   - Within the station details, the value for `id` is the station ID that is required for all API calls made to the v3 endpoint. The value for `legacy_id` is the station ID that is required for all API calls made to non-v3 endpoints.
   - Sample output [JSON File](https://michiganstate.sharepoint.com/sites/Geography-EnviroweatherTeam/_layouts/15/download.aspx?UniqueId=89604a6e8b0e49f0add8f5bb09395ad4&e=BTgnXN) may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Campbell_Info_JSONs?csf=1&web=1&e=Z5sMyO).
   
3. Find available measurements

   - Unfortunately, Campbell does not provide an endpoint that returns all available measurements data. End-user must specify a measurements/list of measurements in order to retrieve station data.
   - To do so, one must find the list of measurements that are available for a station. Following call needs to be made for this task:

   | Component      | Contents                                                     |
   | -------------- | ------------------------------------------------------------ |
   | Header         | Authorization: Bearer ACCESS_TOKEN                           |
   | Method         | GET                                                          |
   | URL            | https://api.campbellcloud.io/v3/campbell-cloud/organizations/{organization_id}/stations/{station_id}/definitions?brief=true |
   | Path Parameter | {organization_id} - `organization_id` from the user details, {station_id} - `id` from the station details (for v3 endpoint) |
   
   - Within the station information, `name` of each measurement is required
   - Sample output [JSON File](https://michiganstate.sharepoint.com/sites/Geography-EnviroweatherTeam/_layouts/15/download.aspx?UniqueId=382fec6e42724095a8c545d47a80e6c2&e=p9K2bS) may be viewed from the project [SharePoint Folder](https://michiganstate.sharepoint.com/:f:/r/sites/Geography-EnviroweatherTeam/Shared%20Documents/Data%20on%20Demand/ADS%20ENVWX%20API%20Project/Vendor%20API%20and%20station%20info/Campbell_Info_JSONs?csf=1&web=1&e=ifojXS).
   
4. Receive data from a station over a specified time period

   - To receive the data for a single/multiple measurement(s) over a specified time period, the following call need to be made:

   | Component      | Contents                                                     |
   | -------------- | ------------------------------------------------------------ |
   | Header         | Authorization: Bearer ACCESS_TOKEN                           |
   | Method         | GET                                                          |
   | URL            | https://api.campbellcloud.io/api_v2/measurement/timeseries/{station_id}/{epoch_start}/{epoch_end}/{measurement_name_1},{measurement_name_2} |
   | Path Parameter | {station_id} - `legacy_id` from the station details (for non-v3 endpoint), {epoch_start} - start date/time in epoch time (milliseconds), {epoch_end} - end date/time in epoch time (milliseconds), {measurement_name_1} - `name` from the station information, {measurement_name_2} - `name` from the station information (optional) |
   - Start and End date/time is expected to be in ***Local Time zone***
   > NOTE: End-user may add as many measurements as one would like. Ensure that the end-user is using a comma between each measurement one is is listing.
   
4. Addtional Endpoint information

   - Full information about the Campbell Cloud API can be found at https://docs.campbellcloud.io/api/. This site includes all available API calls, their correct use and formatting.
   - Additionally product manual may be located at https://help.campbellsci.com/cloud-en/home.htm.

### Variable mapping

- Required Parameters

| Name           | Contents                                                   | Type     |
| -------------- | ---------------------------------------------------------- | -------- |
| username       | Login username for Campbell Cloud Web Portal               | str      |
| user_passwd    | Login password for Campbell Cloud Web Portal               | str      |
| station_id     | `id` from the station details (for v3 endpoint)            | str      |
| station_lid    | `legacy_id` from the station details (for non-v3 endpoint) | str      |
| start_datetime | Start date and time                                        | datetime |
| end_datetime   | End date and time                                          | datetime |

- Usage

```python
params = {
    'username': LOGIN_USERNAME,
    'user_passwd': LOGIN_PASSWORD,
    'station_id': STATION_ID,
    'station_lid': LEGACY_STATION_ID,
    'start_datetime': datetime.strptime('11-19-2021 14:00', '%m-%d-%Y %H:%M'),
    'end_datetime': datetime.strptime('11-19-2021 16:00', '%m-%d-%Y %H:%M')
}
cparams = CampbellParam(**params)
creadings = CampbellReadings(cparams)
print(creadings.response) # print raw JSON response
print(creadings.parsed_resp) # print parsed result in list of dict format
```

### Data Matching/Parsing

TBA
