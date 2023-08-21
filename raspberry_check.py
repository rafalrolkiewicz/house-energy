"""
Program for checking (on another computer) if site rafalrolkiewicz.com is up and running.
It uses Selenium for checking website, telegram bot for sending messages,
subprocess for checking if computer is connected to wifi (reconnect if necessary)
and schedule for scheduling website check every 5 minutes.
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import message_sender as telegram
import schedule
import time
from datetime import datetime
import subprocess
from dotenv import load_dotenv
import os


load_dotenv()

NETWORK_NAME = os.getenv("NETWORK_NAME")
NETWORK_PSWRD = os.getenv("NETWORK_PSWRD")
HOTSPOT_NAME = os.getenv("HOTSPOT_NAME")
HOTSPOT_PSWRD = os.getenv("HOTSPOT_PSWRD")

network = (NETWORK_NAME, NETWORK_PSWRD)
hostpot = (HOTSPOT_NAME, HOTSPOT_PSWRD)


class Driver:
    def __init__(self):
        try:
            self.chrome_options = webdriver.ChromeOptions()
            self.chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            self.chrome_options.add_argument("--headless")
            self.service = Service(
                executable_path=ChromeDriverManager().install())
            self.driver = webdriver.Chrome(
                service=self.service, options=self.chrome_options)

        except Exception as e:
            print(
                f"{datetime.now().replace(microsecond=0)} Failed to load Selenium driver: {e}")


driver = Driver()


def scan_wifi_networks():
    try:
        networks = subprocess.check_output(
            ["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-s"]).decode("utf-8").splitlines()
        network_names = []
        for network in networks:
            network = network.split(" ")
            for item in network:
                if item:
                    network_names.append(item)
                    break
        return network_names
    except subprocess.CalledProcessError:
        return []


def connect_to_wifi(network):
    try:
        subprocess.run(["networksetup", "-setairportpower", "en1", "on"])
    except:
        pass

    try:
        subprocess.run(["networksetup", "-setairportnetwork",
                       "en1", network[0], network[1]])
        print(f"Connected to {network[0]}")
    except subprocess.CalledProcessError:
        print(f"Failed to connect to {network[0]}")


def turn_off_wifi():
    try:
        subprocess.run(["networksetup", "-setairportpower", "en1", "off"])
        print("Disconnected from Wi-Fi")
    except subprocess.CalledProcessError:
        print("Failed to disconnect from Wi-Fi")


def get_connected_network():
    try:
        output = subprocess.check_output(
            ["networksetup", "-getairportnetwork", "en1"], stderr=subprocess.STDOUT).decode("utf-8")
        lines = output.splitlines()

        for line in lines:
            if "Current Wi-Fi Network" in line:
                network_name = line.split(":")[1].strip()
                return network_name
    except subprocess.CalledProcessError as e:
        print("Error:", e)
    return None


def is_connected():
    """
    Check if computer has access to internet by sending ping to Google.
    """
    try:
        subprocess.run(["ping", "-c", "1", "8.8.8.8"], check=True,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        pass
    return False


online_alert = True


def check_site():
    """
    Check if website rafalrolkiewicz.com is up and running.
    """
    global driver
    global online_alert

    if not is_connected():
        connect_to_wifi(network)

    browser = driver.driver

    try:
        browser.get("http://www.rafalrolkiewicz.com")
        wait = WebDriverWait(browser, 10)
    except:
        print(
            f"{datetime.now().replace(microsecond=0)} Error, couldn't load rafalrolkiewicz.com")
        telegram.send_message(
            f"{datetime.now().replace(microsecond=0)} Error, couldn't load rafalrolkiewicz.com!")

    try:
        ngrok_visit_site_ngrok = wait.until(EC.presence_of_element_located((
            By.XPATH, '//*[@id="root"]/div/main/div/div/section[1]/div/footer/button')))
        ngrok_visit_site_ngrok.click()
    except:
        # print("Ngrok site not present or failed")
        pass

    try:
        site = wait.until(EC.presence_of_element_located(
            (By.XPATH, '//*[@id="react-entry-point"]/div/div[2]/div[1]/h1')))
        if site.text == 'ELECTRICITY PRODUCTION' and online_alert == True:
            print(f"{datetime.now().replace(microsecond=0)} Site online.")
            telegram.send_message(
                f"{datetime.now().replace(microsecond=0)} Raspberry online!")
            online_alert = False
        elif site.text != 'ELECTRICITY PRODUCTION':
            print("Site offline!")
            telegram.send_message(
                f"{datetime.now().replace(microsecond=0)} Raspberry offline!")
            online_alert = True
    except:
        print("Site offline!")
        telegram.send_message(
            f"{datetime.now().replace(microsecond=0)} Raspberry offline!")
        online_alert = True
    browser.get("http://www.google.com")


schedule.every(5).minutes.do(check_site)
schedule.run_all()

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
