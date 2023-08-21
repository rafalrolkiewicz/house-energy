"""
This program is used to download data from the energy provider's website
using web scraping. It extracts daily power meter readings and updates
the database with the new values.
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from sqlalchemy import (create_engine,
                        Column,
                        Integer,
                        Date,)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, declarative_base
import message_sender as telegram
import requests


load_dotenv()

LOGIN = os.getenv("SCRAPER_LOGIN")
PASSWORD = os.getenv("SCRAPER_PASSWORD")

Base = declarative_base()
engine = create_engine("sqlite:///electricity.db")


class MyPowerMeter(Base):
    __tablename__ = "my_power_meter"
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    taken = Column(Integer)
    given = Column(Integer)
    taken_daily = Column(Integer)
    given_daily = Column(Integer)


Session = sessionmaker(bind=engine)
session = Session()


def login():
    """
    Logs into a website using provided login credentials.

    Returns:
    - True: If login is successful.
    - False: If login fails due to a captcha lock or any other reason.
    """
    LOGIN = os.getenv("SCRAPER_LOGIN")
    PASSWORD = os.getenv("SCRAPER_PASSWORD")
    try:
        driver.get("https://mojlicznik.energa-operator.pl/dp/UserLogin.do")
        wait = WebDriverWait(driver, 10)
        login_radio = wait.until(
            EC.element_to_be_clickable((By.ID, "loginRadio")))
        login_radio.click()
        user = wait.until(
            EC.presence_of_element_located((By.ID, "j_username")))
        psw = wait.until(
            EC.presence_of_element_located((By.ID, "j_password")))
        user.send_keys(LOGIN)
        psw.send_keys(PASSWORD)
        submit = wait.until(
            EC.element_to_be_clickable((
                By.XPATH, '//*[@id="loginForm"]/div[4]/button'))
        )
        submit.click()
        loged_in = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "digit1")))

        return True

    except:
        captcha = driver.find_elements(By.CLASS_NAME, "errorInfo")
        if captcha.get_attribute("innerHTML") == \
                "Proszę przepisać tekst z obrazka":
            telegram.send_message("Error, captcha lock")
        captcha_img = driver.find_element_by_xpath('//*[@id="captchaacc"]')
        captcha_url = captcha_img.get_attribute("src")
        response = requests.get(captcha_url)
        with open(f"captchas/captcha{datetime.now()}.png", "wb") as file:
            file.write(response.content)

        return False


def download_data():
    """
    Downloads data from a web page and returns the electricity taken and given.

    Returns:
    - electricity_taken (int): The total electricity taken.
    - electricity_given (int): The total electricity given.
    """
    data = []
    digits = driver.find_elements(By.CLASS_NAME, "digit1")
    for i in range(16):
        data.append(digits[i].get_attribute("innerHTML"))

    data2 = []
    after_comma = driver.find_elements(By.CLASS_NAME, "afterComa")
    for j in range(8):
        data2.append(after_comma[j].get_attribute("innerHTML"))

    electricity_taken = data[0:8] + data2[0:4]
    electricity_given = data[8:16] + data2[4:8]
    electricity_taken = int("".join(map(str, electricity_taken)))
    electricity_given = int("".join(map(str, electricity_given)))
    return electricity_taken, electricity_given


def get_todays_date():
    return datetime.now().date()


def save_data():
    """
    Downloads data from an external source, calculates the daily usage
    and saves it to a database.
    """
    date = get_todays_date()
    taken, given = download_data()
    last_row = session.query(MyPowerMeter).order_by(MyPowerMeter
                                                    .id.desc()).first()
    taken_yesterday = last_row.taken
    given_yesterday = last_row.given
    taken_daily = taken - taken_yesterday
    given_daily = given - given_yesterday
    last_row.taken_daily = taken_daily
    last_row.given_daily = given_daily
    session.add(last_row)

    new_row = MyPowerMeter(date=date, taken=taken, given=given)
    session.add(new_row)
    session.commit()
    print(
        f"\n{datetime.now().date()} Success, downloaded and saved data. Date: \
            {date}, taken: {taken/10000}, given: {given/10000}, \
                taken yesterday: {taken_daily/10000}, given yesterday: {given_daily/10000}"
    )


def is_data_actual():
    """
    This function checks if the last row of data in MyPowerMeter table has
    the same date as today's date. Returns True if the last row has the same
    date as today's date, False otherwise.
    """
    today = get_todays_date().strftime("%j")
    last_row = session.query(MyPowerMeter).order_by(
        MyPowerMeter.id.desc()).first()
    last_row_date = last_row.date.strftime("%j")

    if last_row_date == today:
        return True
    else:
        return False


def close_program():
    """
    Closes the driver and session used for web scraping.
    This function closes the driver and session used for web scraping,
    freeing up system resources.
    """
    driver.close()
    driver.quit()
    session.close()


if __name__ == "__main__":
    # Check if the data in database is actual
    if is_data_actual():
        print(f"{datetime.now().date()} Success, data is actual.")

    # If the data is not actual, open a Chrome browser
    else:
        chrome_options = webdriver.ChromeOptions()
        chrome_options.binary_location = (
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        )
        service = Service(executable_path=ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        # if logged in successfully, download and save data to database
        if login():
            save_data()

        else:
            telegram.send_message("Can't log in to Energa!")

        close_program()
