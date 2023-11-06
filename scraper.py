import os
import time
from datetime import datetime
import multiprocessing
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from sqlalchemy import create_engine, Column, Integer, Date, MetaData, Table, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, declarative_base


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
    LOGIN = os.getenv("SCRAPER_LOGIN")
    PASSWORD = os.getenv("SCRAPER_PASSWORD")
    driver.get("https://mojlicznik.energa-operator.pl/dp/UserLogin.do")
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "loginRadio"))).click()
    user = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "j_username")))
    psw = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "j_password")))
    user.send_keys(LOGIN)
    psw.send_keys(PASSWORD)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located(
        (By.XPATH, '//*[@id="loginForm"]/div[4]/button'))).click()


def download_data():
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


def write_to_db():
    date = get_todays_date()
    taken, given = download_data()
    last_row = session.query(MyPowerMeter).order_by(
        MyPowerMeter.id.desc()).first()
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
        f"\n{datetime.now().date()} Success, downloaded and saved data. Date: {date}, taken: {taken/10000}, given: {given/10000}, taken yesterday: {taken_daily/10000}, given yesterday: {given_daily/10000}"
    )


def is_data_actual():
    today = get_todays_date().strftime("%j")
    last_row = session.query(MyPowerMeter).order_by(
        MyPowerMeter.id.desc()).first()
    last_row_date = last_row.date.strftime("%j")

    if last_row_date == today:
        return True
    else:
        return False


def close_program():
    driver.close()
    driver.quit()
    session.close()


if __name__ == "__main__":
    if not is_data_actual():
        # print("Downloading data...")
        service = Service('/usr/lib/chromium-browser/chromedriver')
        driver = webdriver.Chrome(service=service)
        login()
        write_to_db()
        close_program()
    else:
        print(f"{datetime.now().date()} Success, data is actual.")
