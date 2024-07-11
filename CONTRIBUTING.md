# Contributing to Enviroweather Personal Weather Station Database (EWXPWSDB) 🌦️

Welcome to the EWX PWS DB project! We're excited to have you contribute. This guide will help you set up your development environment, understand the project's structure, and provide guidelines to ensure smooth collaboration.

## Table of Contents

1. [Getting Started 🚀](#getting-started-)
2. [Setting Up the Development Environment 🛠️](#setting-up-the-development-environment-)
   - [Installing Poetry](#installing-poetry)
   - [Installing Dependencies](#installing-dependencies)
   - [Activating the Virtual Environment](#activating-the-virtual-environment)
3. [Database Setup 🗄️](#database-setup-)
   - [Installing PostgreSQL](#installing-postgresql)
   - [Setting Up the Database](#setting-up-the-database)
4. [Running Tests 🧪](#running-tests-)
   - [Getting Test Data](#getting-test-data)
   - [Running Tests](#running-tests)
   - [Test Options](#test-options)
   - [Example](#example)
5. [Creating a Merge Request (MR) 📤](#creating-a-merge-request-mr-)
6. [Coding Standards 🧹](#coding-standards-)
7. [Using the CLI](#using-the-cli)
8. [Starting the API](#starting-the-api)
   - [Starting a Dev API Server](#starting-a-dev-api-server)
   - [Using the API](#using-the-api)
9. [Docker Setup 🐳](#docker-setup-)
   - [Building the Docker Image](#building-the-docker-image)
   - [Running the Docker Container](#running-the-docker-container)
10. [Additional Resources 📚](#additional-resources-)

## Getting Started 🚀

1. **Fork the repository** on GitLab.
2. **Clone your fork** to your local machine:
   ```bash
   git clone https://gitlab.msu.edu/your-username/ewxpwsdb.git
   cd ewxpwsdb
   ```

## Setting Up the Development Environment 🛠️

We use [Poetry](https://python-poetry.org) for dependency management and packaging. Follow the instructions below to set up your environment.

### Installing Poetry

#### Recommended: Using `pipx`

1. **Install `pipx`**:
   ```bash
   python -m pip install --user pipx
   python -m pipx ensurepath
   ```

2. **Install Poetry**:
   ```bash
   pipx install poetry
   ```

#### Alternative: Using the Official Installer

Refer to the [Poetry documentation](https://python-poetry.org/docs/#installation) for alternative installation methods.

### Installing Dependencies

Once Poetry is installed, run the following commands to install the project dependencies:

```bash
poetry install
```

### Activating the Virtual Environment

To activate the virtual environment created by Poetry, run:

```bash
poetry shell
```

## Database Setup 🗄️

We use PostgreSQL for our database. Follow these steps to set up your database environment.

### Installing PostgreSQL

#### macOS

We recommend using [Postgres.app](https://postgresapp.com).

1. **Download and install Postgres.app**.
2. **Start the server and create a new database** (e.g., `ewxpws`).

#### Windows & Linux

Refer to the [PostgreSQL official installation guide](https://www.postgresql.org/download/) for your operating system.

### Setting Up the Database

1. **Create a `.env` file** in the project root directory and set the database URL:
   ```ini
   EWXPWSDB_URL=postgresql+psycopg2://user:password@localhost:5432/ewxpws
   ```

2. **Initialize the database**:
   ```bash
   poetry run python -m ewxpwsdb.db.database init_db
   ```

## Running Tests 🧪

### Getting Test Data

Ensure you have the test stations file (`data/test_stations.tsv`). This file contains credentials and is required for running tests.

### Running Tests

To run the tests, use the following command:

```bash
poetry run pytest tests
```

### Test Options

For custom test options, you can use:

```bash
poetry run pytest tests --station_type=STATION_TYPE --dburl=DBURL --file=FILE --no-import
```

### Example

To run tests for a specific station type:

```bash
poetry run pytest tests --station_type=ZENTRA
```

## Creating a Merge Request (MR) 📤

1. **Create a new branch** for your work:
   ```bash
   git checkout -b issue-number-description
   ```

2. **Make your changes** following the coding standards.

3. **Commit your changes** with a descriptive message, including the issue number:
   ```bash
   git commit -m "Fix issue #123: Corrected off-by-one error"
   ```

4. **Push your branch** to your fork:
   ```bash
   git push origin issue-number-description
   ```

5. **Create a merge request** on GitLab and fill in the template. Make sure to select:
   - `Delete source branch when merge request is accepted.`
   - `Squash commits when merge request is accepted.`

6. **Request a review** from the project maintainers.

## Coding Standards 🧹

To ensure consistency and readability, adhere to the following standards:

- **PEP 8**: Follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide.
- **Docstrings**: Write clear and concise docstrings for all public methods and classes.
- **Type Annotations**: Use type annotations to specify the expected types of function arguments and return values.
- **Commit Messages**: Write meaningful commit messages that describe what the commit does.

## Using the CLI

There is a command line interface for working with the database and APIs using the terminal/command.exe.

1. **List all stations**:
   ```bash
   poetry run ewxpws station list
   ```

2. **Get current weather details, directly from API**:
   ```bash
   poetry run ewxpws weather {station code}
   ```

3. **Get recent hourly weather summary from database**:
   ```bash
   poetry run ewxpws hourly {station code}
   ```

For many of these commands, there are options for `--start` and `--stop` to get a range of data. For hourly data, these are dates in the form `YYYY-MM-DD`.

## Starting the API

To start the API server on your local computer, use the command line script:

```bash
poetry run ewxpws startapi -d <database_url>
```

This runs on host address `http://0.0.0.0:8000`, but the host IP and the port address can be overridden. The server can be run using SSL with local cert and key files, with the `--ssl` option (off by default).

### Starting a Dev API Server

For development with FastAPI, set the database variable in `.env` and run:

```bash
poetry run fastapi dev src/ewxpwsdb/api/http_api.py
```

This will auto-reload as code changes.

To run with a different database (e.g., on a different server), add the URL to the environment:

```shell
source .env
EWXPWSDB_URL=$EWXPWSDB_AWS_URL; poetry run fastapi dev src/ewxpwsdb/api/http_api.py
```

### Using the API

Once the server is running, browse to `http://0.0.0.0:8000/docs` for documentation about the API. Several other routes are available. For example, `http://0.0.0.0:8000/stations` lists station codes. All data is output in JSON format.

## Docker Setup 🐳

This includes a simplistic `Dockerfile` to run the API server for giving out the data. It copies all files (including `/data` which is not needed except to initialize the DB).

### Building the Docker Image

To build a new image:

```bash
TAG=v0; docker buildx build -t ewxpwsdb:$TAG .
```

### Running the Docker Container

To run the container:

```bash
docker run -d --env-file=docker.env -p 80:80 ewxpwsdb:v0
```

Ensure you have a `.env` file to support Docker with an external DB URL and cert locations. Example `.env` contents:

```ini
EWXPWSDB_URL=postgresql+psycopg2://localhost:5432/ewxpws
EWXPWSDB_DOCKER_URL=postgresql+psycopg2://ewxuser:password@ewxpwsdev-db.etc.us-east-1.rds.amazonaws.com:5432/ewxpws
```

To use this from the command line:

```shell
source .env; docker run -d --env-file=docker.env  -e EWXPWSDB_URL=$EWXPWSDB_D

OCKER_URL  -p 80:80 ewxpwsdb:v0
```

## Additional Resources 📚

- [Poetry Documentation](https://python-poetry.org/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Documentation](https://docs.docker.com/)

Thank you for contributing! Your efforts help make this project better. If you have any questions, feel free to reach out to the project maintainers. 🙌
```