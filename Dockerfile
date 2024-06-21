FROM python:3.11-buster
RUN pip install poetry
COPY . .
RUN poetry install

ENTRYPOINT ["poetry", "run", "python", "-m", "ewxpwsdb.api.http_api", "--port", "80"]
