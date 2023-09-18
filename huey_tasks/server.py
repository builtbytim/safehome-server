import subprocess
import sys
import os
from lib.logging import Logger

logger = Logger(f"{__package__}.{__name__}")

# Command to start the Huey consumer process
# --logfile=./logs/huey.log

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

command = "huey_consumer.py main.huey"

try:
    # Run the command in the terminal
    subprocess.run(command, shell=True, check=True)
except subprocess.CalledProcessError as e:

    logger.error(f"An error occurred starting huey consumer : {e} ")
