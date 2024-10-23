# Developed By Keagan Bowman
# Live telemetry stream handling for the Blue Raven flight controller
#
# telemetry_handler.py
from __future__ import annotations

import re
import serial
import threading
import db_handler
from psycopg2.extensions import connection

"""
# regex expression for the telemetry data. the resulting groups (on a successful match) should look like the following:
group 1: current year
group 2: current month
group 3: current day
group 4: current time
groups 5-7: hi-G Acceleration X, Y, Z (in Gs  x100)
groups 8-10: Acceleration X, Y, Z (in Gs x1000)
groups 11, 12: barometric pressure (atm x10000) and temperature (x100)
group 13: battery voltage (in mV)
groups 14-16: gryo X, Y, Z (in deg/sec x100)
groups 17, 18: tilt angle, roll angle  (in degrees x10)
group 19: vertical velocity (feet/sec)
group 20: altitude above ground level (feet)
"""

TELEMETRY_RE = re.compile(r"([0-9]*)\s([0-9]*)\s([0-9]*)\s([0-9]*:[0-9]*:[0-9]*.[0-9]*)\sHG:\s*(-?[0-9]*)\s*(-?["
                          r"0-9]*)\s*(-?[0-9]*)\s*XYZ:\s*(-?[0-9]*)\s*(-?[0-9]*)\s*(-?[0-9]*)\s*Bo:\s*(-?[0-9]*)\s*("
                          r"-?[0-9]*)\s*bt:\s*(-?[0-9]*)\s*gy:\s*(-?[0-9]*)\s*(-?[0-9]*)\s*(-?[0-9]*)\s*ang:\s*(-?["
                          r"0-9]*)\s*(-?[0-9]*)\s*vel\s*(-?[0-9]*)\s*AGL\s*(-?[0-9]*)")


def get_telemetry(db: connection, device: int) -> dict:
    """
    Grabs telemetry logged in database by a specific device, parses it, and returns a dictionary
    :return:
    """

    # grab most recent data from the database
    data = db_handler.get_recent_data(db, device)

    # match data with regex string
    try:
        data = TELEMETRY_RE.findall(data)[0]
    except IndexError:
        # data not found, return empty telemetry
        return {"ERROR": "NO MATCHING DATA FOUND"}

    # assign telemetry data.
    # this is ordered in the way it shows up on the live video
    telemetry = {
        "Vert. Velocity": f"{data[18]} f/s",
        "Acceleration": f"{data[7]} {data[8]} {data[9]}",
        "Altitude": f"{data[19]} feet",
        "Tilt": f"{int(data[16]) / 10:.1f} deg.",
        "Roll": f"{int(data[17]) / 10:.1f} deg.",
        "spacer1": "",  # this is a spacer element to separate the utility info from other telemetry
        "Timestamp": data[3],
        "Battery": f"{int(data[12]) / 1000:.2f} V",
        "Temp": f"{int(data[11]) / 100:.2f} F"

    }

    return telemetry


def start_raven_streams(db: connection, ports: list[str]) -> list[int]:
    """
    Start the Blue Raven monitor program
    :param db: Database connection
    :param ports: Ports to attempt to connect to
    :return: A list of the devices IDs in the order the ports were passed in
    """
    threads = []
    device_ids = []

    # loop through all given ports for the raven streams
    for port in ports:
        # attempt to get the device ID
        device = db_handler.get_device(db, port)

        # check if device was found
        if device is None:
            # no device found, create a new one
            device = db_handler.add_device(db, port)

        # grab device IDs
        device_ids.append(device)

        # create new thread and append it to thread list
        threads.append(threading.Thread(target=telemetry_reader, args=[port, device]))

    # start threads
    for thread in threads:
        thread.start()

    # return collected device IDs
    return device_ids


def telemetry_reader(port: str, device: int):
    """
    Telemetry reader made to run in a separate thread
    :param port: Port where serial stream is located
    :param device: id of the device being read
    :return:
    """

    # create database connection
    db = db_handler.establish_db()

    # create connection to port
    conn = serial.Serial(
        port=port,
        baudrate=921600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE
    )

    # close the connection if it already exists
    if conn.is_open:
        conn.close()

    # open connection
    conn.open()

    # mark port as active in database
    db_handler.set_device_status(db, device, True)

    while True:
        # read in data until next carriage return
        data = conn.read_until(b"\r")

        # add data to database
        db_handler.add_data(db, device, data)
