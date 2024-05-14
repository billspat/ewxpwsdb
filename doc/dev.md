# Enviroweather Personal Weather Stations Database (ewxpwsdb)

## Instructions for developers

Requirements: 

- Python 3.10 or higher installed 
- Python Poetry Package manager: https://python-poetry.org. You may have to install this for your system rather than in an virtual environment
- A local copy or access to a remote Postgresql Database server.   This has been tested with version 15 but earlier or later versions should work
  - Masc version for local testing https://postgresapp.com 
  - Windows version for local testing, this is often e version from EDB: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
- File with our test-bed weather stations information and API access secrets.  

1. Install Poetry: 

   - on Mac, we use homebrew works brew install python; brew install poetry.   
   - Windows... ?
    
    you can run   poetry --help  to see if it's installed

1. clone the repo after you've been given access 

    `git clone git@gitlab.msu.edu:Enviroweather/ewxpwsdb.git`

    optionally specify a new folder 

    `git clone git@gitlab.msu.edu:Enviroweather/ewspwsdb.git ewxpwsdb_project`  # or whatever folder you like

1. go to the code directory 

   The poetry commands should be run in the project folder <br>
   `cd ewxpwsdb`  # replace if you used a different directory name


3. use poetry to create an enviroment with all the dependencies installed

   do this in the root directory of the project

    '--no-root' means: don't also install the package itself -- not super critical but let's try it this way.   See `poetry install --help` for more info

    `poetry install --no-root`

1. get the station data

    you need the file with weather station information and secrets, which is a tab-separated value file (TSV).  See the `/data` folder for an example

    copy the station csv file into the `/data` folder of this project.  

1. to work in the terminal with the poetry virtual env, use this command 

    `poetry shell`

    this gives you a new prompt and uses the env that poetry just created.  This is very similar to virtualenv `source venv/bin/activate`

1. now you can run tests inside this shell

    `pytest tests`

1.  in VS code, select the poetry env


    to have code open this folder

    use the command prompt (on mac is shift+command+p)  and search for  "python select interpreter..."

    it should pick the poetry env for you.  

    in my vs code, the correct Poetry env is automatically selected.  
    in my case on Mac, the Poetry env path ilooks something like this: 

    `~/Library/Caches/pypoetry/virtualenvs/ewxpwsdb-XXXX-py3.11`