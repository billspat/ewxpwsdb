FROM python:3.11-buster
RUN pip install poetry
COPY . .
RUN poetry install
# use the internal CLI to start the api server, requires .env configured SSL files available
ENTRYPOINT ["poetry", "run", "ewxpws", "startapi","--ssl"]
