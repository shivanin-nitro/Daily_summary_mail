#!/bin/bash

# This script is used to run the Daily Summary Mail pipeline via cron job
# It activates the virtual environment and runs the main pipeline

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the project directory
cd "$SCRIPT_DIR"

# Activate the virtual environment
source .venv/bin/activate

# Run the Python pipeline
python main.py

# Deactivate the virtual environment
deactivate
