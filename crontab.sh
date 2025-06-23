#!/bin/bash

# Get the absolute path of the script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load environment variables
if [ -f "${SCRIPT_DIR}/.env" ]; then
    export $(grep -v '^#' "${SCRIPT_DIR}/.env" | xargs)
fi
echo ${SCRIPT_DIR}
# Change to script directory and run crawler
cd "${SCRIPT_DIR}" && \
. ./.venv/bin/activate && \
python "${SCRIPT_DIR}/strava_leaderboard_crawler.py"