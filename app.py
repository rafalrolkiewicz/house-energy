"""
This program creates a web-based dashboard using Dash and Plotly to display
various energy-related data. The dashboard connects to a SQLite database
containing tables for energy consumption, solar panel production, weather data
and power meter readings.

The program defines several SQLAlchemy classes representing the tables in
the database. These classes are used to fetch data from the database
and update the dashboard.

The main features of the dashboard include:

1. Real-time updates:
   - The dashboard automatically refreshes at regular intervals
   to display the latest data.

2. Energy Production Gauge:
   - A gauge chart displays the real-time solar panel production in Watts (W).
   - The chart also shows the total solar energy produced today
   in kilowatt-hours (kWh).

3. Daily Production Line Chart:
   - The line chart shows the solar panel production in Watts (W)
   throughout a selected day.
   - It also displays the total solar energy produced on that day
   in kilowatt-hours (kWh).

4. Monthly Production Bar Chart:
   - The bar chart displays the daily solar energy production
   for a selected month.
   - It also shows the total solar energy produced in that month
   in kilowatt-hours (kWh).

5. Heater Consumption Line Chart:
   - The line chart shows the energy consumption of a heater throughout
   a selected day in kilowatt-hours (kWh).
   - It also displays the total heater consumption today and
   the total consumption for the selected day.

6. Power Meter Line Chart:
   - The line chart displays the energy consumption and production from
   a power meter for a selected month.
   - It also shows the total taken and given energy in kilowatt-hours (kWh)
   for that month, along with the difference.

7. Rooms Temperatures Line Chart:
   - The line chart displays the temperatures in different rooms
   and outside temperature throughout a selected day.

8. Dropdowns and Date Pickers:
   - Dropdowns and date pickers allow users to select the desired month
   or date for data visualization.

The dashboard is served on a local server and listens on port 8050.
It utilizes Dash Bootstrap Components for styling and layout
and Plotly graph objects for interactive and dynamic visualizations.
"""


import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    DateTime,
    Date,
    Float,
    func,
    String,
    desc,
)
from sqlalchemy.orm import sessionmaker, declarative_base
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta


app = dash.Dash(
    __name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "/assets/styles.css"]
)
app.title = "House Energy"
Base = declarative_base()
engine = create_engine("sqlite:///electricity.db")
refreshes = 0


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


class MyPowerMeter(Base):
    __tablename__ = "my_power_meter"
    id = Column(Integer, primary_key=True)
    date = Column(Date)
    taken = Column(Integer)
    given = Column(Integer)
    taken_daily = Column(Integer)
    given_daily = Column(Integer)


def add_one_month(dt):
    """
    Add one month to the given date.

    This function takes a datetime object as input and returns
    a new datetime object with one month added to the original date.
    If the resulting month is greater than 12,
    the year will be incremented as well.

    Parameters:
        dt (datetime): A datetime object representing the input date.

    Returns:
        datetime: A new datetime object with one month added to the input date.
    """
    year = dt.year
    month = dt.month
    month += 1
    if month > 12:
        month = 1
        year += 1
    new_date = datetime(year=year, month=month, day=1)

    return new_date


def available_months(start_month, start_year):
    """
    Get a list of available datetime objects starting from the specified month
    and year until the current month and year.

    This function generates a list of datetime objects,
    representing the first day of each month, starting from the specified
    start_month and start_year until the current month and year.

    Parameters:
        start_month (int): The starting month.
        start_year (int): The starting year.

    Returns:
        list: A list of datetime objects representing dates
        from picked up date to present day.

    Example (ran in 2023-08):
        >>> available_months(6, 2023)
        [datetime.datetime(2023, 6, 1),
         datetime.datetime(2023, 7, 1),
         datetime.datetime(2023, 8, 1),

    Note:
        - The current month and year are determined based on the
        system's current date and time.
    """
    dates_to_pick = []
    start_time = datetime(year=start_year, month=start_month, day=1)
    current_month = datetime.now().replace(day=1)
    count = True
    while count:
        # dates_to_pick.append(start_time.strftime("%Y-%m"))
        dates_to_pick.append(start_time)
        start_time = add_one_month(start_time)
        # print(start_time)
        if (
            start_time.year == current_month.year
            and start_time.month == current_month.month + 1
        ):
            count = False

    return dates_to_pick


def generate_dropdown_options(month, year):
    """
    Generate dropdown options for a Dash app based on available months.

    This function takes a starting month and year as input and generates
    a list of dictionary objects representing dropdown options suitable
    for a Dash app. The dropdown options correspond to the available months
    starting from the provided month and year until the current month and year.

    Parameters:
        month (int): The starting month.
        year (int): The starting year.

    Returns:
        list: A list of dictionary objects, each containing 'label'
        and 'value' keys.'label' corresponds to the formatted month and year
        (e.g., "08-2023"), and 'value' corresponds to the formatted year
        and month (e.g., "2023-08").

    Example (ran in 2023-08):
        >>> generate_dropdown_options(6, 2023)
        [{'label': '06-2023', 'value': '2023-06'},
         {'label': '07-2023', 'value': '2023-07'},
         {'label': '08-2023', 'value': '2023-08'}]

    Note:
        - The current month and year are determined based on the system's
        current date and time.
        - The function uses the 'available_months' function to get
        the list of available months.
    """
    options = [
        {
            "label": f"{start_time.strftime('%m-%Y')}",
            "value": f"{start_time.strftime('%Y-%m')}",
        }
        for start_time in available_months(month, year)
    ]

    return options


app.layout = html.Div(
    [
        html.Link(rel="icon", href="/assets/favicon.ico", type="image/x-icon"),
        dcc.Store(id="refresh-count-storage", data=0),
        dbc.Row([html.P(" ")]),
        dbc.Container(
            className="container",
            style={
                "padding": "20px",
                "max-width": "auto",
                "margin": "0 auto",
                "border": "2px solid black",
            },
            children=[
                # First Main Row
                dbc.Row(
                    [html.H1("ELECTRICITY PRODUCTION",
                             style={"text-align": "center"})]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            id="yield-value",
                            className="yield-value",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([dcc.Graph(id="gauge-chart")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.H5("PICK A DAY:",
                                 style={"text-align": "center"})]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.Div(
                            dcc.DatePickerSingle(
                                id="production_day_picker",
                                date=datetime.now().replace(
                                    hour=0, minute=0, second=0),
                                min_date_allowed=datetime(2023, 7, 12),
                                max_date_allowed=datetime.now()
                                .replace(hour=1),
                                display_format="DD-MM-YYYY",
                                first_day_of_week=1,
                            ),
                            style={
                                "text-align": "center"
                            },  # Center the date picker within the div
                        )
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            id="yield-that-day",
                            className="yield-that-day",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([dcc.Graph(id="production_by_day_chart")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.H5("PICK A MONTH:",
                                 style={"text-align": "center"})]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        dcc.Dropdown(
                            id="month-dropdown_bar",
                            options=generate_dropdown_options(4, 2022),
                            value=datetime.now().strftime("%Y-%m"),
                            placeholder="Select a month",
                            clearable=False,
                            style={"width": "150px", "margin": "0 auto"},
                        ),
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            id="months-sum",
                            className="months-sum",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([dcc.Graph(id="yield-bar-chart")]),
                dcc.Interval(id="interval-component",
                             interval=5000, n_intervals=0),
                html.Div(id="refresh-count", style={"display": "none"}),
            ],
        ),
        dbc.Row([html.P(" ")]),
        dbc.Container(
            className="container",
            style={
                "padding": "20px",
                "max-width": "auto",
                "margin": "0 auto",
                "border": "2px solid black",
            },
            children=[
                dbc.Row(
                    [html.H1("ELECTRIC HEATER DATA",
                             style={"text-align": "center"})]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            id="forward-energy-todays-value",
                            className="forward-energy-todays-value",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.H5("PICK A DAY:",
                                 style={"text-align": "center"})]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.Div(
                            dcc.DatePickerSingle(
                                id="heater_day_picker",
                                date=datetime.now()
                                .replace(hour=0, minute=0, second=0),
                                min_date_allowed=datetime(2023, 7, 17),
                                max_date_allowed=datetime.now()
                                .replace(hour=1),
                                display_format="DD-MM-YYYY",
                                first_day_of_week=1,
                            ),
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            id="forward-energy-daily-value",
                            className="forward-energy-daily-value",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([dcc.Graph(id="heater-chart")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.H5("PICK A MONTH:",
                                 style={"text-align": "center"})]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        dcc.Dropdown(
                            id="month-dropdown_bar_heater",
                            options=generate_dropdown_options(8, 2023),
                            value=datetime.now().strftime("%Y-%m"),
                            placeholder="Select a month",
                            clearable=False,
                            style={"width": "150px", "margin": "0 auto"},
                        ),
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            id="heater-months-sum",
                            className="months-sum",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([dcc.Graph(id="heater-bar-chart")]),
            ],
        ),
        dbc.Row([html.P(" ")]),
        dbc.Container(
            className="container",
            style={
                "padding": "20px",
                "max-width": "auto",
                "margin": "0 auto",
                "border": "2px solid black",
            },
            children=[
                dbc.Row(
                    [html.H1("ELECTRIC METER DATA",
                             style={"text-align": "center"})]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.P(
                            "ELECTRICITY METER READING",
                            style={"text-align": "center"}
                        )
                    ]
                ),
                dbc.Row(
                    [
                        html.P(
                            id="power-meter-taken",
                            className="power-meter-taken",
                            style={"text-align": "center", "color": "red"},
                        )
                    ]
                ),
                dbc.Row(
                    [
                        html.P(
                            id="power-meter-given",
                            className="power-meter-given",
                            style={"text-align": "center  ", "color": "green"},
                        )
                    ]
                ),
                dbc.Row(
                    [
                        html.P(
                            id="meter-diff",
                            className="power-meter-given",
                            style={"text-align": "center  "},
                        )
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.H5("PICK A MONTH:",
                                 style={"text-align": "center"})]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        dcc.Dropdown(
                            id="meter-month-dropdown",
                            options=generate_dropdown_options(11, 2022),
                            value=datetime.now().strftime("%Y-%m"),
                            placeholder="Select a month",
                            clearable=False,
                            style={"width": "150px", "margin": "0 auto"},
                        ),
                    ]
                ),
                dbc.Row(
                    [
                        dcc.Graph(
                            id="power-meter-line-chart",
                        )
                    ]
                ),
            ],
        ),
        dbc.Row([html.P(" ")]),
        dbc.Container(
            className="container",
            style={
                "padding": "20px",
                "max-width": "auto",
                "margin": "0 auto",
                "border": "2px solid black",
            },
            children=[
                dbc.Row(
                    [
                        html.H1(
                            "ROOMS AND OUTSIDE TEMPERATURE",
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.P(" ")]),
                dbc.Row([html.H5("PICK A DAY:",
                                 style={"text-align": "center"})]),
                dbc.Row([html.P(" ")]),
                dbc.Row(
                    [
                        html.Div(
                            dcc.DatePickerSingle(
                                id="temperature-date-picker",
                                date=datetime.now()
                                .replace(hour=0, minute=0, second=0),
                                min_date_allowed=datetime(2023, 7, 17),
                                max_date_allowed=datetime.now()
                                .replace(hour=1),
                                display_format="DD-MM-YYYY",
                                first_day_of_week=1,
                            ),
                            style={"text-align": "center"},
                        )
                    ]
                ),
                dbc.Row([html.P(" ")]),
                dbc.Row([dcc.Graph(id="rooms_temperatures_chart")]),
            ],
        ),
    ]
)


@app.callback(
    Output("refresh-count", "children"),
    Input("interval-component", "n_intervals")
)
def update_timestamp(n):
    """
    Update the timestamp and refresh count for a Dash app.

    This callback function is triggered by the 'n_intervals' property
    of an interval component in the Dash app. It updates the timestamp
    and refresh count, which are displayed in the terminal.

    Parameters:
        n (int): The number of times the interval has been triggered
        (automatically passed).

    Returns:
        str: A string representing the timestamp and refresh count.

    Note:
        - The function uses the global variable 'refreshes' to keep track of
        the refresh count.
        - The timestamp is generated using the current date and time with
        microseconds set to 0.
        - The 'n' parameter is automatically passed by the Dash framework
        and represents the
          number of times the interval has been triggered.
        - The output of this function is displayed in the terminal.
    """
    global refreshes
    refreshes += 1
    time_stamp = datetime.now().replace(microsecond=0)
    print(f"{time_stamp} Refreshes: {refreshes}")


# Update the gauge chart and today's yield value
@app.callback(
    Output("gauge-chart", "figure"),
    Output("yield-value", "children"),
    Input("interval-component", "n_intervals"),
)
def update_production_now_gauge(n):
    """
    Update the data for the production gauge chart and yield today value.

    This function is a callback that fetches the latest 'SolaxData' record
    from the database and calculates the live production value for
    the gauge chart. It also calculates the yield today value and formats
    the data suitable for updating the production gauge chart in a Dash app.

    Parameters:
        n (int): The number of times the callback has been triggered
        (automatically passed).

    Returns:
        tuple: A tuple containing two elements:
            - dict: A dictionary containing 'data' formatted for
            the production gauge chart.
            - str: A string representing the yield today value.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    # Fetch the latest SolaxData value
    solax_data_now = session.query(SolaxData).order_by(desc(
        SolaxData.date)).first()
    time_difference = datetime.now() - solax_data_now.date
    threshold = timedelta(minutes=5)

    # Check if the time difference is greater than the threshold
    if time_difference > threshold:
        live_production_now = 0
    else:
        # Prepare the data for the gauge chart
        live_production_now = (
            solax_data_now.live_production if solax_data_now else 0
        )  # Default to 0 if no data
    yield_today = solax_data_now.yield_today if solax_data_now else 0

    gauge_data = [
        {
            "type": "indicator",
            "mode": "gauge+number",
            "value": live_production_now,
            "number": {"suffix": "W"},
            "title": {"text": "NOW:"},
            "gauge": {
                "axis": {"range": [None, 10000]},
                "steps": [
                    {"range": [0, 2000], "color": "black"},
                    {"range": [2000, 4000], "color": "gray"},
                    {"range": [4000, 6000], "color": "darkgray"},
                    {"range": [6000, 8000], "color": "lightgray"},
                    {"range": [8000, 10000], "color": "white"},
                ],
                "threshold": {
                    "line": {"color": "green", "width": 4},
                    "thickness": 0.75,
                    "value": live_production_now,
                },
            },
        }
    ]

    session.close()

    return {"data": gauge_data}, f"SUM TODAY: {yield_today} kWh"


@app.callback(
    Output("production_by_day_chart", "figure"),
    Output("yield-that-day", "children"),
    Input("production_day_picker", "date"),
)
def update_production_in_day_chart(selected_date):
    """
    Update the production chart for the selected day and display
    the yield that day.

    This function is a callback that fetches data from the 'SolaxData' table
    based on the selected date and creates a Plotly figure to display
    the production in a selected day chart. It also fetches the yield for
    the selected day and formats the data suitable for updating the chart
    and displaying the yield value in a Dash app.

    Parameters:
        selected_date (str): The selected date in the format 'YYYY-MM-DD'.

    Returns:
        tuple: A tuple containing two elements:
            - go.Figure: A Plotly figure containing the production chart.
            - str: A string representing the yield for the selected day.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    if not selected_date:
        return {}

    selected_date = pd.to_datetime(selected_date)
    # print(selected_date)

    # Filter the data based on the selected date
    start_time = selected_date
    end_time = selected_date + pd.offsets.MonthEnd()

    query = (
        session.query(SolaxData.date, SolaxData.live_production)
        .filter(SolaxData.date >= start_time, SolaxData.date < end_time)
        .order_by(SolaxData.date)
    )
    data = query.all()

    yield_data = (
        session.query(SolaxData)
        .filter(SolaxData.date >= start_time, SolaxData.date < end_time)
        .order_by(desc(SolaxData.date))
        .first()
    )
    yield_that_day = yield_data.yield_today if yield_data else 0

    session.close()

    df = pd.DataFrame(data, columns=["Date", "Production"])
    df["Date"] = pd.to_datetime(df["Date"])

    # Set the "Date" column as the index
    df.set_index("Date", inplace=True)

    # Resample the data to calculate averages every 5 minutes
    df = df.resample("5T").mean()

    df["Production"] = df["Production"].round(0)

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Production"],
            mode="lines",
            name="Production",
            line=dict(color="green", shape="spline", smoothing=1),
        )
    )

    fig.update_layout(
        title_text="Day's production:",
        title_x=0.5,
        title_y=0.9,
        plot_bgcolor="#f5f5f5",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="left",
            x=0.01),
    )
    fig.update_xaxes(range=[start_time, end_time])
    fig.update_yaxes(title_text="WATTS")
    fig.update_yaxes(range=[0, 9500])

    # Set the range for the x-axis to display data only from 4:00 to 22:00
    fixed_start_time = selected_date.replace(hour=4, minute=0, second=0)
    fixed_end_time = selected_date.replace(hour=22, minute=0, second=0)
    fig.update_xaxes(range=[fixed_start_time, fixed_end_time])

    return fig, f"SUM {yield_that_day} kWh"


@app.callback(
    Output("yield-bar-chart", "figure"),
    Output("months-sum", "children"),
    Input("month-dropdown_bar", "value"),
)
def update_production_in_month_chart(date):
    """
    Update the production bar chart for the selected month and display
    the total monthly yield.

    This function is a callback that fetches data from the 'SolaxData' table
    based on the selected month and year. It then creates a Plotly bar chart
    to display the daily yields for the selected month and calculates
    the total monthly yield. The data is formatted appropriately for updating
    the bar chart and displaying the total monthly yield value in a Dash app.

    Parameters:
        date (str): The selected date in the format 'YYYY-MM'.

    Returns:
        tuple: A tuple containing two elements:
            - go.Figure: A Plotly figure containing the production bar chart.
            - str: A string representing the total monthly yield in kWh.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    if date is None:
        return {}

    # Filter the data based on the selected month and year
    start_date = pd.to_datetime(f"{date}-01")
    end_date = start_date + pd.offsets.MonthEnd()

    subquery = (
        session.query(func.max(SolaxData.date).label("max_date"))
        .filter(SolaxData.date >= start_date, SolaxData.date <= end_date)
        .group_by(func.strftime("%Y-%m-%d", SolaxData.date))
    )

    data = session.query(SolaxData).filter(SolaxData.date.in_(subquery)).all()

    # Create a DataFrame to store the data
    df = pd.DataFrame(
        [(item.date.day, item.yield_today) for item in data],
        columns=["Day", "Yield"]
    )
    months_sum = round(df["Yield"].sum(), 2)
    months_sum = "{:,.2f}".format(months_sum).replace(",", " ")
    # Create the bar chart
    fig = go.Figure(data=go.Bar(x=df["Day"], y=df["Yield"]))

    # Add the bar trace
    for i, yield_value in enumerate(df["Yield"]):
        fig.add_annotation(
            x=df["Day"][i],
            y=yield_value + 2,
            text=str(yield_value),  # Convert the yield value to a string
            showarrow=False,  # Hide the arrow
        )

    fig.update_layout(
        title_text=f"Month's production: {date}",
        plot_bgcolor="#f5f5f5",
        title_x=0.5,
        title_y=0.9,
    )
    fig.update_yaxes(title_text="kWh")
    fig.update_yaxes(range=[0, 80])
    fig.update_traces(marker=dict(color="green"))

    session.close()

    return fig, f"SUM: {months_sum} kWh"


@app.callback(
    Output("heater-chart", "figure"),
    Output("forward-energy-todays-value", "children"),
    Output("forward-energy-daily-value", "children"),
    Input("heater_day_picker", "date"),
)
def update_heater_chart(selected_date):
    """
    Update the energy consumption line chart for the selected date and display
    heater consumption information.

    This function is a callback that fetches data from the 'TuyaData' table
    based on the selected date. It then calculates the hourly energy
    consumption and creates a Plotly line chart to display the energy
    consumption throughout the day. The data is formatted appropriately
    for updating the line chart and displaying the heater consumption
    information in a Dash app.

    Parameters:
        selected_date (str): The selected date in the format 'YYYY-MM-DD'.

    Returns:
        tuple: A tuple containing three elements:
            - go.Figure: A Plotly figure containing the energy consumption
            line chart.
            - str: A string representing the heater consumption today in kWh.
            - str: A string representing the total consumption for
            the selected day in kWh.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    if not selected_date:
        return {}

    selected_date = pd.to_datetime(selected_date)

    # Filter the data based on the selected date
    start_time = selected_date
    end_time = selected_date + pd.offsets.Day()

    query = (
        session.query(TuyaData.date, TuyaData.forward_energy)
        .filter(TuyaData.date >= start_time, TuyaData.date < end_time)
        .order_by(TuyaData.date)
    )
    data = query.all()
    tuya_data_now = session.query(TuyaData).order_by(
        desc(TuyaData.date)).first()
    tuya_data_that_day = (
        session.query(TuyaData)
        .filter(TuyaData.date >= start_time, TuyaData.date < end_time)
        .order_by(desc(TuyaData.date))
        .first()
    )
    heater_that_day = (
        tuya_data_that_day.forward_energy_daily if tuya_data_that_day else 0
    )

    session.close()

    forward_energy_todays_value = (
        round(tuya_data_now.forward_energy_daily, 2) if tuya_data_now else None
    )
    df = pd.DataFrame(data, columns=["Date", "Energy"])

    # Calculate energy consumption in each hour
    df["Hour"] = df["Date"].dt.hour
    df_grouped = df.groupby("Hour").agg({"Energy": ["min", "max"]})
    df_grouped["Hourly_Energy"] = (
        df_grouped["Energy", "max"] - df_grouped["Energy", "min"]
    )

    # Generate date-time for each hour
    df_grouped["Date"] = pd.to_datetime(
        selected_date.strftime("%Y-%m-%d ")
        + df_grouped.index.astype(str) + ":00:00"
    )

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=df_grouped["Date"],
            y=df_grouped["Hourly_Energy"],
            mode="lines",
            name="Energy Consumption",
            line=dict(color="red", shape="spline", smoothing=1),
        )
    )

    fig.update_layout(
        title_text="Day's consumption:",
        title_x=0.5,
        title_y=0.9,
        plot_bgcolor="#f5f5f5",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="left",
            x=0.01),
    )
    fig.update_yaxes(title_text="kWh")
    fig.update_yaxes(range=[0, 8.5])

    return (
        fig,
        f"HEATER CONSUMPTION TODAY: {forward_energy_todays_value} kWh",
        f"SUM {round(heater_that_day, 2)} kWh",
    )


@app.callback(
    Output("heater-bar-chart", "figure"),
    Output("heater-months-sum", "children"),
    Input("month-dropdown_bar_heater", "value"),
)
def update_heater_in_month_chart(date):
    """
    Update the heater consumption bar chart for the selected month and display
    the total monthly yield.

    This function is a callback that fetches data from the 'TuyaData' table
    based on the selected month and year. It then creates a Plotly bar chart
    to display the daily consumption for the selected month and calculates
    the total monthly consumption. The data is formatted appropriately for updating
    the bar chart and displaying the total monthly consumption value in a Dash app.

    Parameters:
        date (str): The selected date in the format 'YYYY-MM'.

    Returns:
        tuple: A tuple containing two elements:
            - go.Figure: A Plotly figure containing the consumption bar chart.
            - str: A string representing the total monthly consumption in kWh.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    if date is None:
        return {}

    # Filter the data based on the selected month and year
    start_date = pd.to_datetime(f"{date}-01")
    end_date = start_date + pd.offsets.MonthEnd()

    subquery = (
        session.query(func.max(TuyaData.date).label("max_date"))
        .filter(TuyaData.date >= start_date, TuyaData.date <= end_date)
        .group_by(func.strftime("%Y-%m-%d", TuyaData.date))
    )

    data = session.query(TuyaData).filter(TuyaData.date.in_(subquery)).all()

    # Create a DataFrame to store the data
    df = pd.DataFrame(
        [(item.date.day, item.forward_energy_daily) for item in data],
        columns=["Day", "Consumption"]
    )
    months_sum = round(df["Consumption"].sum(), 2)
    months_sum = "{:,.2f}".format(months_sum).replace(",", " ")

    # Create the bar chart
    fig = go.Figure(data=go.Bar(x=df["Day"], y=df["Consumption"]))

    # Add the bar trace
    for i, consumption_value in enumerate(df["Consumption"]):
        fig.add_annotation(
            x=df["Day"][i],
            y=consumption_value + 4,

            # Convert the consumption value to a string
            text=str(round(consumption_value, 2)),
            showarrow=False,  # Hide the arrow
        )

    fig.update_layout(
        title_text=f"Month's consumption: {date}",
        plot_bgcolor="#f5f5f5",
        title_x=0.5,
        title_y=0.9,
    )
    fig.update_xaxes(range=[start_date, end_date])
    fig.update_yaxes(title_text="kWh")
    fig.update_yaxes(range=[0, 160])
    fig.update_traces(marker=dict(color="red"))

    session.close()

    return fig, f"SUM: {months_sum} kWh"


@app.callback(
    Output("power-meter-line-chart", "figure"),
    Output("power-meter-taken", "children"),
    Output("power-meter-given", "children"),
    Output("meter-diff", "children"),
    Input("meter-month-dropdown", "value"),
)
def update_meter_chart(date):
    """
    Update the taken and given line chart for the selected month and display
    power meter information.

    This function is a callback that fetches data from the 'MyPowerMeter'
    table based on the selected month and year. It then creates a Plotly line
    chart to display the daily taken and given values for the selected month.
    The data is formatted appropriately for updating the line chart
    and displaying the power meter information in a Dash app.

    Parameters:
        date (str): The selected date in the format 'YYYY-MM'.

    Returns:
        tuple: A tuple containing four elements:
            - go.Figure: A Plotly figure containing taken and given line chart.
            - str: A string representing the total taken value in kWh.
            - str: A string representing the total given value in kWh.
            - str: A string representing the difference between
            taken and given values in kWh.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    if date is None:
        return {}

    # Filter the data based on the selected month and year
    start_date = pd.to_datetime(f"{date}-01")
    end_date = start_date + pd.offsets.MonthEnd()

    # Fetch data for chart
    # 1. Taken daily from my_power_meter table
    taken_daily_data = (
        session.query(MyPowerMeter.date, MyPowerMeter.taken_daily)
        .filter(MyPowerMeter.date >= start_date, MyPowerMeter.date <= end_date)
        .all()
    )

    # 2. Given daily from my_power_meter table
    given_daily_data = (
        session.query(MyPowerMeter.date, MyPowerMeter.given_daily)
        .filter(MyPowerMeter.date >= start_date, MyPowerMeter.date <= end_date)
        .all()
    )

    # 3. Power meter read
    power_meter_now = (
        session.query(MyPowerMeter).order_by(desc(MyPowerMeter.date)).first()
    )
    taken_value = round(power_meter_now.taken / 10000, 2) \
        if power_meter_now else None
    given_value = round(power_meter_now.given / 10000, 2) \
        if power_meter_now else None
    meter_diff = taken_value - given_value
    taken_formatted = "{:,.2f}".format(taken_value).replace(",", " ")
    given_formated = "{:,.2f}".format(given_value).replace(",", " ")
    meter_diff = "{:,.2f}".format(meter_diff).replace(",", " ")

    # Create DataFrames to store the fetched data
    df_taken = pd.DataFrame(taken_daily_data, columns=["Date", "Taken Daily"])
    df_given = pd.DataFrame(given_daily_data, columns=["Date", "Given Daily"])

    # Divide taken_daily and given_daily values by 10000
    df_taken["Taken Daily"] = df_taken["Taken Daily"] / 10000
    df_given["Given Daily"] = df_given["Given Daily"] / 10000

    # Create the bar chart
    fig = go.Figure()
    fig.update_layout(
        bargap=0.2,
        plot_bgcolor="#f5f5f5",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="right",
            x=0.25),
        barmode='group'  # This is needed for double bar chart
    )

    # Add the "Taken Daily" bar
    fig.add_trace(
        go.Bar(
            x=df_taken["Date"],
            y=df_taken["Taken Daily"],
            name="Taken",
            marker_color='red'
        )
    )

    # Add the "Given Daily" bar
    fig.add_trace(
        go.Bar(
            x=df_given["Date"],
            y=df_given["Given Daily"],
            name="Given",
            marker_color='green'
        )
    )

    fig.update_layout(
        title_text=f"Month's taken and given: {date}", title_x=0.5, title_y=0.9
    )
    fig.update_xaxes(range=[start_date, end_date])
    fig.update_yaxes(title_text="kWh")
    fig.update_yaxes(range=[0, 160])

    session.close()

    return (
        fig,
        f"Total Taken: {taken_formatted} kWh",
        f"Total Given: {given_formated} kWh",
        f"Diff: {meter_diff} kWh",
    )


@app.callback(
    Output("rooms_temperatures_chart", "figure"),
    Input("temperature-date-picker", "date"),
)
def update_temperatures_chart(selected_date):
    """
    Update temperatures in rooms and outside temperature.

    This function is a callback that fetches data from the 'TuyaData' table
    and 'WeatherData' table based on the selected day. It then creates
    a Plotly line chart to display temperatures.

    Parameters:
        date (str): The selected date in the format 'YYYY-MM-DD'.

    Returns:
        - go.Figure: A Plotly figure containing rooms and outside temperatures.
    """
    Session = sessionmaker(bind=engine)
    session = Session()

    if not selected_date:
        return {}

    selected_date = pd.to_datetime(selected_date)

    # Filter the data based on the selected date
    start_time = selected_date
    end_time = selected_date + pd.offsets.Day()

    # Fetch the data for "bathroom_lower" and "bedrooms" columns
    query = (
        session.query(
            TuyaData.date,
            TuyaData.bathroom_lower,
            TuyaData.first_bedroom,
            TuyaData.second_bedroom,
            TuyaData.third_bedroom,
        )
        .filter(TuyaData.date >= start_time, TuyaData.date < end_time)
        .order_by(TuyaData.date)
    )

    data = query.all()

    weather_query = (
        session.query(WeatherData.date, WeatherData.weather_temperature_feels)
        .filter(WeatherData.date >= start_time, WeatherData.date < end_time)
        .order_by(WeatherData.date)
    )
    weather_data = weather_query.all()

    session.close()

    # Create DataFrames to store the fetched data
    df = pd.DataFrame(
        data,
        columns=[
            "Date",
            "Bathroom",
            "First Bedroom",
            "Second Bedroom",
            "Third Bedroom",
        ],
    )
    df["Date"] = pd.to_datetime(df["Date"])

    # Set the "Date" column as the index
    df.set_index("Date", inplace=True)

    # Resample the data to calculate averages every 5 minutes
    df = df.resample("5T").mean()

    temperature_columns = [
        "Bathroom",
        "First Bedroom",
        "Second Bedroom",
        "Third Bedroom",
    ]
    df[temperature_columns] = df[temperature_columns].round(1)

    df_weather = pd.DataFrame(weather_data,
                              columns=["Date", "Outside temperature"])
    df_weather["Date"] = pd.to_datetime(df_weather["Date"])

    # Set the "Date" column as the index
    df_weather.set_index("Date", inplace=True)

    # Resample the data to calculate averages every 5 minutes
    df_weather = df_weather.resample("5T").mean()
    df_weather["Outside temperature"] = \
        df_weather["Outside temperature"].round(1)
    # Create the line chart
    fig = go.Figure()

    # Add the "Bathroom Lower" line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Bathroom"],
            mode="lines",
            name="Bathroom",
            line=dict(color="hotpink", shape="spline", smoothing=1),
        )
    )

    # Add the "First Bedroom" line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["First Bedroom"],
            mode="lines",
            name="First Bedroom",
            line=dict(color="orange", shape="spline", smoothing=1),
        )
    )

    # Add the "Second Bedroom" line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Second Bedroom"],
            mode="lines",
            name="Second Bedroom",
            line=dict(color="grey", shape="spline", smoothing=1),
        )
    )

    # Add the "Third Bedroom" line
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Third Bedroom"],
            mode="lines",
            name="Third Bedroom",
            line=dict(color="cyan", shape="spline", smoothing=1),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=df_weather.index,
            y=df_weather["Outside temperature"],
            mode="lines",
            name="Outside temperature",
            line=dict(color="brown", shape="spline", smoothing=1),
        )
    )

    fig.update_layout(
        title_text="Temperatures:",
        title_x=0.5,
        title_y=0.9,
        plot_bgcolor="#f5f5f5",
        legend=dict(
            orientation="h",
            yanchor="top",
            y=-0.24,
            xanchor="left",
            x=0.01),
    )
    fig.update_yaxes(title_text="Celsius")

    return fig


if __name__ == "__main__":
    app.run_server(host="::", port=8050, debug=False)
