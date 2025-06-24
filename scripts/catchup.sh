#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PACKAGE_DIR="$SCRIPT_DIR/.."
# edit this to match the virtual environment folder
PYENV_DIR=$PACKAGE_DIR/.venv
. $PYENV_DIR/bin/activate
# edit to match file with vars
. $PACKAGE_DIR/.env
export EWXPWSDB_URL=$EWXPWSDB_URL

for station in `ewxpws station -d $EWXPWSDB_URL list`; do
 echo "requesting data for $station... "
 ewxpws catchup -d $EWXPWSDB_URL  $station
done
