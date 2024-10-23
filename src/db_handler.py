# Developed By Keagan Bowman
# Database handler for in-flight data.
# Using postgresql allows the threaded control handlers to insert new data as it arrives, instead of waiting for a
# request by the main video stream
#
# db_handler.py

from __future__ import annotations

import os
import json
import psycopg2
from psycopg2.extensions import connection


def establish_db(wipe_db: bool = False) -> connection:
    """
    Establish a connection to the database, create tables, and wipe tables if needed

    :param .creds: List of strings, laid out like so: [database name, host URL, port, username, password]
    :param wipe_db: Should the database be wiped?
    :return: psycopg2 Database Connection object
    """

    if not os.path.exists("./.creds"):
        raise "Creds file not found at ./.creds"

    with open("./.creds", "r") as f:
        creds = json.load(f)
        f.close()

    db = psycopg2.connect(
        database=creds[0].strip(),
        host=creds[1].strip(),
        port=creds[2].strip(),
        user=creds[3].strip(),
        password=creds[4].strip()
    )

    cursor = db.cursor()

    if wipe_db:
        cursor.execute("DROP TABLE IF EXISTS data CASCADE")
        cursor.execute("DROP TABLE IF EXISTS devices CASCADE")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS devices (
        id SERIAL PRIMARY KEY,
        port TEXT NOT NULL UNIQUE,
        is_active BOOL DEFAULT FALSE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data (
        id SERIAL PRIMARY KEY,
        device INTEGER NOT NULL,
        data TEXT NOT NULL,
        time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (device) REFERENCES devices(id)
    );
    """)

    return db


def add_data(db: connection, device_id: int, data: str | bytes) -> None:
    """
    Add data to the table
    :param db: Database connection
    :param device_id: Device adding data
    :param data: Data string (or bytes) to add to database
    :return: None
    """
    # if the data is in bytes, cast it to a string
    if isinstance(data, bytes):
        data = data.decode("utf-8")

    cursor = db.cursor()

    # add new data to the db
    cursor.execute("INSERT INTO data (device, data) VALUES (%s, %s);", (device_id, data))

    cursor.close()
    db.commit()


def get_recent_data(db: connection, device_id: int) -> str:
    """
    Collects the most recent data string from a given device
    :param db: Database connection
    :param device_id: Device to pull data for
    :return: Most recent data entry in the database
    """
    cursor = db.cursor()

    # select data
    cursor.execute("SELECT data FROM data WHERE device = %s ORDER BY time DESC LIMIT 1;", (device_id,))
    # grab selected data
    data = cursor.fetchone()

    cursor.close()

    # ensure data isn't empty
    if data is None:
        data = ""
    else:
        data = data[0]

    return data


def add_device(db: connection, port: str) -> int:
    """
    Adds a new device to the database
    :param db: Database connection
    :param port: The port identifier of the device
    :return: The ID of the newly inserted device
    """
    cursor = db.cursor()

    # add device to database
    cursor.execute("INSERT INTO devices (port) VALUES (%s) RETURNING id;", (port,))
    # grab id
    new_id = cursor.fetchone()[0]

    # close database & commit
    cursor.close()
    db.commit()

    # return id
    return new_id


def get_device(db: connection, port: str) -> int | None:
    """
    Gets a device by matching the serial port
    :param db: Database connection
    :param port: Port to find
    :return: device's ID if found, None if not found
    """
    cursor = db.cursor()

    # select device
    cursor.execute("SELECT id FROM devices WHERE port = %s;", (port,))
    device = cursor.fetchone()

    cursor.close()

    if device is not None:
        device = device[0]

    return device


def set_device_status(db: connection, device: int, status: bool) -> None:
    """
    Set the status of a device to in-use (True) or inactive (False)
    :param db: Database connection
    :param device: Device ID
    :param status: New status of the device
    :return:
    """
    cursor = db.cursor()

    cursor.execute("UPDATE devices SET is_active = %s WHERE id = %s;", (status, device))

    cursor.close()
    db.commit()


def get_device_status(db: connection, device: int) -> bool | None:
    """
    Get the current activity status of a device
    :param db: Database connection
    :param device: Device to find
    :return: Current status of the device, or None if not found
    """
    cursor = db.cursor()

    # grab status from DB
    cursor.execute("SELECT is_active FROM devices WHERE id = %s;", (device,))
    status = cursor.fetchone()

    cursor.close()

    # check status is found and cast
    if status is not None:
        status = bool(status[0])

    return status


def reset_device_statuses(db: connection):
    """
    Sets the status of all devices to inactive
    :param db: Database connection
    :return:
    """
    cursor = db.cursor()

    # update devices list
    cursor.execute("UPDATE devices SET is_active = FALSE;")

    cursor.close()
    db.commit()
