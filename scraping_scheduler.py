"""
This program schedules a scraper script to run periodically and sends updates
to a Telegram chat. The time_limit function runs the given function with a
time limit of 10 minutes and raises a multiprocessing.TimeoutError if
the function takes longer than 10 minutes to run. The run_scraper function
runs a scraper script to download data from energy provider and returns
the updated update time. It tries to download data everyday at 12:00 PM
and retries every hour if fail. The change_update_time function takes in
two parameters: mode and update_time. Mode is a string that specifies whether
the update time should be incremented by one hour or set up to next day 12PM.
Update_time is a datetime object that represents the current update time.
The function returns a datetime object that represents the next update time.
The main function schedules the scraper script to run periodically
and sends updates to a Telegram chat.
"""

import message_sender as telegram
import multiprocessing
import logging
import subprocess
from datetime import datetime, timedelta
import time

logging.basicConfig(filename="logs/scraping_scheduler_logs.log",
                    level=logging.INFO)


def time_limit(function, update_time):
    """
    Runs the given function with a time limit of 10 minutes (600 seconds).

    Parameters:
        function: The function to run.
        update_time: The current update time.

    Returns:
        The updated update time

    Raises:
        multiprocessing.TimeoutError: If the function takes
        longer than 10 minutes to run.

    """
    pool = multiprocessing.Pool(processes=1)
    result = pool.apply_async(function)
    pool.close()

    try:
        result.get(timeout=600)
        pool.join()
    except multiprocessing.TimeoutError:
        # Timeout occurred, terminate the pool
        pool.terminate()
        pool.join()

    if result.ready():
        update_time = result.get()
    else:
        print("Timeout occurred")
        telegram.send_message("Timeout occurred")
        update_time = change_update_time("next_hour", update_time)

    return update_time


def run_scraper():
    """
    Runs a scraper script and returns the update time.

    Returns:
    datetime: The updated update time after running scraper.py.

    """
    command = ["python", "scraper.py"]
    result = subprocess.run(command, capture_output=True)

    output = result.stdout.decode("utf-8")
    error = result.stderr.decode("utf-8")

    print(str(output))
    if output:
        telegram.send_message(str(output))

    if "Success" in str(output):
        update_time = change_update_time("next_day", datetime.now())
    else:
        update_time = change_update_time("next_hour", datetime.now())
        print(f"Error occurred{str(error)}")
        telegram.send_message(f"Error occurred{str(error)}")

    logging.info(f"Command: {command}")
    logging.info(f"Output: {output}")
    logging.info(f"Error: {error}")

    return update_time


def change_update_time(mode, update_time):
    """
    This function takes in two parameters: mode and update_time.
    Mode is a string that specifies whether the update time should be
    incremented by one hour or one day. Update_time is a datetime object that
    represents the current update time. The function returns a datetime object
    that represents the next update time.

    Parameters:
    mode (str): A string that specifies whether the update time should be
    incremented by one hour or one day.
    update_time (datetime): A datetime object that represents
    the current update time.

    Returns:
    datetime: A datetime object that represents the next update time.
    """
    if mode == "next_day":
        update_time = update_time + timedelta(days=1)
        update_time = update_time.replace(
            hour=12, minute=0, second=0, microsecond=0)
        print(f"{update_time} Next update time")
        telegram.send_message(f"{update_time} Next update time")

    elif mode == "next_hour":
        update_time = update_time + timedelta(hours=1)
        update_time = update_time.replace(microsecond=0)
        print(f"{update_time} Next update try time")
        telegram.send_message(f"{update_time} Next update try time")

    return update_time


if __name__ == "__main__":
    update_time = datetime.now()
    while True:
        now = datetime.now()
        # if it's time to update
        if update_time < now:
            # run scraper with time limit of 10 minutes
            # if scraper fail to download data, try every hour to success
            update_time = time_limit(run_scraper, update_time)
        time.sleep(1)
