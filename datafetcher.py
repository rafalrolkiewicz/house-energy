"""
This program is responsible for fetching data from various APIs, including
the Weather API, Tuya Thermostats, Tuya Sub Meter, and Photovoltaic API.
It stores the collected data in the electricity.db SQLite database.

The program performs the following tasks:
- Imports necessary modules and packages
- Defines constants and IDs for API endpoints and devices
- Creates database tables using SQLAlchemy
- Defines classes for data storage in the database
- Defines a context manager for database sessions
- Defines functions for downloading data from external APIs
- Defines functions for saving data to the database
- Defines a function to calculate daily energy consumption
- Sets up a scheduler to periodically save data to the database
- Runs the scheduler in an infinite loop

Note: The program relies on environment variables for API keys
and other sensitive information.
"""

# import logging
import os
import time
from datetime import datetime, date
import json
import requests
from contextlib import contextmanager
from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import schedule
import message_sender as telegram
from tuya_connector import (
    TuyaOpenAPI,
    # TUYA_LOGGER,
)

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WEATHER_URL = (
    f"http://api.openweathermap.org/data/2.5/weather?q=Gdansk&appid={WEATHER_API_KEY}"
)

ACCESS_ID = os.getenv("TUYA_ACCESS_ID")
ACCESS_KEY = os.getenv("TUYA_ACCESS_KEY")
API_ENDPOINT = "https://openapi.tuyaeu.com"
MQ_ENDPOINT = "wss://mqe.tuyaeu.com:8285/"

# IDS
heaters = {
    "Bathroom upper": "bf9a7af096e9126993qwbs",
    "Bathroom lower": "bfd96cbeb0ec1c0143lelg",
    "First bedroom": "bfaaf79511bbe1897cowpo",
    "Second bedroom": "bff62b27dfe5e20f9a0bav",
    "Third bedroom": "bf15606f24b52affa6gvlo",
}
SMART_METER_ID = "bfa7eff5705ba20638xbng"

SOLAX_URL = os.getenv("SOLAX_URL")

Base = declarative_base()
engine = create_engine("sqlite:///electricity.db")


class TuyaData(Base):
    __tablename__ = "tuya_data"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    forward_energy = Column(Float)
    forward_energy_daily = Column(Float)
    bathroom_upper = Column(Float)
    bathroom_lower = Column(Float)
    first_bedroom = Column(Float)
    second_bedroom = Column(Float)
    third_bedroom = Column(Float)


class SolaxData(Base):
    __tablename__ = "solax_data"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    yield_today = Column(Float)
    live_production = Column(Float)


class WeatherData(Base):
    __tablename__ = "weather_data"
    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    weather_temperature = Column(Float)
    weather_temperature_feels = Column(Float)
    weather_humidity = Column(Float)
    weather_pressure = Column(Float)
    weather_wind = Column(Float)
    weather_wind_direction = Column(Float)
    weather_clouds = Column(Float)
    weather_description = Column(String)


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """
    A context manager that provides a transactional scope around
    a series of database operations.

    Yields:
        session: A SQLAlchemy session object.

    Exception:
        If an error occurs during the database operations
        telegram message is sent.

    Finally:
        No matter the result session is closed.
    """
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        print("Error: Session scope failed")
        telegram.send_message("Error: Session scope failed")
        # raise
    finally:
        session.close()


def download_solax_data():
    """
    Downloads data from the Solax API
    and returns the yield today and live production.

    Returns:
    - yield_today (float): The total energy yield for the day in kWh.
    - live_production (float): The current power output in watts.

    If the API request fails, an error message is printed
    and a message is sent via Telegram.
    """
    response = requests.get(SOLAX_URL)

    if response.status_code == 200:
        data = json.loads(response.text)
        yield_today = data["result"]["yieldtoday"]
        live_production = data["result"]["acpower"]

        return yield_today, live_production

    else:
        print("Error: Could not retrieve data from Solax")
        telegram.send_message("Error: Could not retrieve data from Solax")


def download_tuya_data():
    """
    Downloads data from Tuya API for all heaters and smart meter.

    Returns:
    - total_energy (float): Total energy usage in kWh from the smart meter.
    - heaters_responses (dict): Dictionary containing temperatures
      in each room.
    """
    try:
        # Enable debug log
        # TUYA_LOGGER.setLevel(logging.DEBUG)

        # Init openapi and connect
        openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
        openapi.connect()

        heaters_responses = {}

        for name, id in heaters.items():
            response = openapi.get(f"/v1.0/iot-03/devices/{id}/status", dict())
            response = response["result"][1]["value"] / 10
            heaters_responses.update({name: response})

        total_energy = (
            openapi.get(f"/v1.0/iot-03/devices/{SMART_METER_ID}/status", dict())[
                "result"
            ][0]["value"]
            / 100
        )

        return total_energy, heaters_responses

    except:
        print("Error: Could not retrive data from TUYA")
        telegram.send_message("Error: Could not retrive data from TUYA")


def download_weather_data():
    """
    Downloads weather data from a specified URL and returns a tuple of
    relevant weather information.

    Returns:
    Tuple of weather information including:
    - weather_temperature (float): temperature in Celsius
    - weather_temperature_feels (float): feels like temp in Celsius
    - weather_humidity (int): humidity percentage
    - weather_pressure (int): pressure in hPa
    - weather_wind (float): wind speed in m/s
    - weather_wind_direction (int): wind direction in degrees
    - weather_clouds (int): cloudiness percentage
    - weather_description (str): description of weather conditions
    """
    response = requests.get(WEATHER_URL)
    if response.status_code == 200:
        data = json.loads(response.text)
        weather_temperature = round(data["main"]["temp"] - 273.15, 2)
        weather_temperature_feels = round(
            data["main"]["feels_like"] - 273.15, 2)
        weather_humidity = data["main"]["humidity"]
        weather_pressure = data["main"]["pressure"]
        weather_wind = data["wind"]["speed"]
        weather_wind_direction = data["wind"]["deg"]
        weather_clouds = data["clouds"]["all"]
        weather_description = data["weather"][0]["description"]

        return (
            weather_temperature,
            weather_temperature_feels,
            weather_humidity,
            weather_pressure,
            weather_wind,
            weather_wind_direction,
            weather_clouds,
            weather_description,
        )

    else:
        print("Error: Could not retrieve data from Weather API")
        telegram.send_message(
            "Error: Could not retrieve data from Weather API")


def calculate_forward_energy_daily(row):
    today = date.today()
    with session_scope() as session:
        todays_first_forward_energy = (
            session.query(TuyaData)
            .filter(TuyaData.date <= today)
            .order_by(TuyaData.date.desc())
            .with_entities(TuyaData.forward_energy)
            .first()
        )
    if todays_first_forward_energy is not None:
        row.forward_energy_daily = (
            row.forward_energy - todays_first_forward_energy[0])
    else:
        row.forward_energy_daily = 0.0

    return row


def save_all_data_to_db():
    """
    Downloads data from various sources and saves it to the database.

    Returns:
        None

    Raises:
        Exception: Sends message via Telegram if there is an error
        downloading or saving the data.

    """
    try:
        solax_data = download_solax_data()
        if solax_data:
            solax_to_db = SolaxData(
                date=datetime.now().replace(microsecond=0),
                yield_today=solax_data[0],
                live_production=solax_data[1],
            )
    except:
        print("Error: Could not download Solax data to database")
        telegram.send_message(
            "Error: Could not download Solax data to database")

    try:
        tuya_data = download_tuya_data()
        if tuya_data:
            tuya_to_db = TuyaData(
                date=datetime.now().replace(microsecond=0),
                forward_energy=tuya_data[0],
                bathroom_upper=tuya_data[1]["Bathroom upper"],
                bathroom_lower=tuya_data[1]["Bathroom lower"],
                first_bedroom=tuya_data[1]["First bedroom"],
                second_bedroom=tuya_data[1]["Second bedroom"],
                third_bedroom=tuya_data[1]["Third bedroom"],
            )
            tuya_to_db = calculate_forward_energy_daily(tuya_to_db)
    except:
        print("Error: Could not download Tuya data to database")
        telegram.send_message(
            "Error: Could not download Tuya data to database")

    try:
        weather_data = download_weather_data()
        if weather_data:
            weather_to_db = WeatherData(
                date=datetime.now().replace(microsecond=0),
                weather_temperature=weather_data[0],
                weather_temperature_feels=weather_data[1],
                weather_humidity=weather_data[2],
                weather_pressure=weather_data[3],
                weather_wind=weather_data[4],
                weather_wind_direction=weather_data[5],
                weather_clouds=weather_data[6],
                weather_description=weather_data[7],
            )
    except:
        print("Error: Could not download Weather data to database")
        telegram.send_message(
            "Error: Could not download Weather data to database")

    try:
        with session_scope() as session:
            session.add(solax_to_db)

    except:
        print("Error: Could not save Solax data to database")
        telegram.send_message("Error: Could not save Solax data to database")

    try:
        with session_scope() as session:
            session.add(tuya_to_db)

    except:
        print("Error: Could not save Tuya data to database")
        telegram.send_message("Error: Could not save Tuya data to database")

    try:
        with session_scope() as session:
            session.add(weather_to_db)

    except:
        print("Error: Could not save Weather data to database")
        telegram.send_message("Error: Could not save Weather data to database")


schedule.every(10).seconds.do(save_all_data_to_db)
schedule.run_all()

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
