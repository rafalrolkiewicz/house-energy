"""This program checks if required processes are running, starts them
and sends a message via Telegram if not. It also can stop running Python
process with the given name. The program uses the following functions:

- `ngrok_running()`: Checks if the ngrok process is running. Returns True
if the ngrok process is running, False otherwise.
- `check_running_python_processes()`: Returns a list of the names of all
running Python processes.
- `check_and_run_processes()`: Checks if required processes are running.
Starts them and sends a message via Telegram if not.
- `stop_process(process)`: Stops a running Python process with the given name.

The program uses the `schedule` library to schedule the
`check_and_run_processes()` function to run every 5 seconds,
the `stop_process("app.py")` function to run every day at 00:05,
and the `backup.make_database_backup()` function to run every Monday at 00:00.
The program runs continuously using a `while` loop and
the `schedule.run_pending()` function to execute the scheduled tasks."""


import schedule
import psutil
import message_sender as telegram
import backup
from datetime import datetime
import time
import subprocess
import os
import signal
from dotenv import load_dotenv


load_dotenv()

NETWORK_NAME = os.getenv("NETWORK_NAME")
NETWORK_PSWRD = os.getenv("NETWORK_PSWRD")
HOTSPOT_NAME = os.getenv("HOTSPOT_NAME")
HOTSPOT_PSWRD = os.getenv("HOTSPOT_PSWRD")

network = (NETWORK_NAME, NETWORK_PSWRD)


def is_connected():
    try:
        subprocess.run(["ping", "-c", "1", "8.8.8.8"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        pass
    return False

# version for Ubuntu
def connect_to_wifi(network):
    try:
        subprocess.run(["nmcli", "radio", "wifi", "on"])
    except:
        pass
    try:
        subprocess.run(["nmcli", "dev", "wifi", "connect", network[0], "password", network[1]])
        print(f"Connected to {network[0]}")
    except subprocess.CalledProcessError:
        print(f"Failed to connect to {network[0]}")


def check_wifi_connection():
    if not is_connected():
        connect_to_wifi(network)


def ngrok_running():
    """
    Checks if the ngrok process is running.

    Returns:
    bool: True if the ngrok process is running, False otherwise.
    """
    for process in psutil.process_iter(["pid", "name"]):
        try:
            process_info = process.info
            if "ngrok" in process_info["name"].lower():
                return True

        except psutil.NoSuchProcess:
            # If the process terminated abruptly while iterating, skip it
            pass

    return False


def check_running_python_processes():
    """
    This function returns a list of the names of all running Python processes.

    Returns:
    - python_processes (list): A list of strings representing the names of
    all running Python processes.
    """
    python_processes = []

    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            process_info = process.info
            if "python" in process_info["name"].lower() \
                    and process_info["cmdline"]:
                # Get the script name from the full command line
                script_name = (
                    process_info["cmdline"][1]
                    if len(process_info["cmdline"]) >= 2
                    else "Unknown"
                )
                python_processes.append(script_name)

        except psutil.NoSuchProcess:
            # If the process terminated abruptly while iterating, skip it
            pass
    return python_processes


def check_and_run_processes():
    """
    Checks if required processes are running. Starts them and send message
    via Telegram if not.

    Returns:
        None
    """
    required_processes = ["app.py", "datafetcher.py", "scraping_scheduler.py"]
    running_processes = check_running_python_processes()
    now = datetime.now().replace(microsecond=0)

    for process in required_processes:
        if not process in running_processes:
            try:
                subprocess.Popen(["python", process])
                print(f"{now} {process} has been started.")
                telegram.send_message(f"{now} {process} has been started.")
            except Exception as e:
                print(f"{now} Error starting {process}: {str(e)}")
                telegram.send_message(
                    f"{now} Error starting {process}: {str(e)}")

    if not ngrok_running():
        print(f"{now} Error, Ngrok isn't running")
        telegram.send_message(f"{now} Error, Ngrok isn't running")


def stop_process(process):
    """
    Stop a running Python process with the given name.

    Parameters:
    process (str): The name of the process to stop.

    Returns:
    None

    Raises:
    Exception: If there is an error stopping the process.
    """
    running_processes = check_running_python_processes()

    if process in running_processes:
        try:
            for proc in psutil.process_iter(["cmdline", "pid"]):
                if proc.info["cmdline"] is not None \
                        and process in proc.info["cmdline"]:
                    os.kill(proc.info["pid"], signal.SIGTERM)
                    print(f"{process} has been stopped.")
                    # telegram.send_message(f"{process} has been stopped.")
                    break
        except Exception as e:
            print(f"Error stopping {process}: {str(e)}")
            telegram.send_message(f"Error stopping {process}: {str(e)}")
    else:
        print(f"{process} is not running.")


schedule.every(5).seconds.do(check_and_run_processes)
schedule.every(5).minutes.do(check_wifi_connection())
schedule.every().day.at("00:05").do(stop_process, "app.py")
schedule.every().monday.at("00:00").do(backup.make_database_backup)
schedule.run_all()

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
