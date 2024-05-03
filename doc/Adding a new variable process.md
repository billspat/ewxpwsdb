## Adding a new variable to the system and database

### EWX Personal Weather Stations 


1. Add variable to the model

in `db/models.py` edit the class Reading and add a new field
  - subclass of SqlModel, see https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/
  - for most weather sensors,  add a variable as an optional float with default= None.   
    None indicates no value was created, which is not the same as zero. 
  - example: `wspd  : Optional[float] = Field(default=None, description="average, wind speed, m/s")`

2. Add variable to API tranforms, 

for each API class (SpectrumAPI, ZentraAPI, etc), edit the function `_transform()` which is specific to that vendor type. 

this function is called by the `tranform()` function in the parent class `WeatherAPI` so 
it only has to focus on converting a dictionary of keys and numbers into individual variables.  

Not all station types will support the variable being added, and don't need to add it and fill it with None as the `Reading` model has the 
default as `None` if the variable is not present. 

3. Add tests

in file `test_api_readings.py` is a test function `test_get_responses_and_transform()`

this test uses a database with stations in it and calls the get readings and transforms them.   It then checks that the outputs all look like they should

note that this test function is loaded with many tests (assert statements) becuase of Zentra, which has a 60s delay on all api calls.   
Creating a single large test function means we can test the output from one api call, rathern than repeated api calls, which would take forever. 

( it's possible to refactor this using a fixture that calls the API once and then has many tests on it, but this is how it is now)

IN that test, add checks for all the stations that support this new variable  that it's an actual float

To run the test for a specific station type, use the following syntax, for example DAVIS 

`pytest tests/test_api_readings.py --station_type=DAVIS`

or 

`pytest tests --station_type=DAVIS`

for all tests.  

without the `--station_type` param it runs spectrum station by default.  

4. Add value validation

TBD

this is not part of the codebase yet, but the next step is to add validation of the data by checking a range etc. 

