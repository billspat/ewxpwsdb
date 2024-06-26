FROM python:3.11-buster
RUN pip install poetry
COPY . .
RUN poetry install

# this docker file runs the CLI command 
ENTRYPOINT ["poetry", "run", "ewxpws"]

# and by default starts up a non-dev uvicorn server with SSL
# this requires the certificate files to be available via .env

CMD ["startapi","--port 443", "--ssl"]

## Examples to run this dockerfile
# first ensure there is a file .env on the server in the format required (see readme.md)
# these examples assume the tag used when creating the docker image were ewxpwsdb:latest

# https server on port 443 - requires there are certificates on the server and pointed to by the .env file
# docker run -d -p 443:443 --env-file=.env ewxpwsdb:latest

# http server without SSL for testing
# docker run -d --env-file=.env -p 80:80 ewxpwsdb:latest startapi --port 80 --no-ssl

# use the docker image to get some data from the database from station with code STATIONCODE, and delete the container when completed (otherwise it hangs around)
# in this way you do not need to install anything except for docker (Python etc etc)
# docker run --rm --env-file=.env hourly -s 2024-06-10 -e 2024-06-11 STATIONCODE

# see all the commands you can run 
# docker run --rm -h

