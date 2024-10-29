# Developed By Keagan Bowman
# Program for transcribing live video data from a Runcam 4 v2 and telemetry from two Blue Raven flight controllers
# into a single video for transmission using RPI GPIO headers to a radio video transmitter
#
# main.py
from __future__ import annotations

# TODO:
# add camera discovery

import cv2
import json
import time
import qrcode
import db_handler
import numpy as np
import overlay_utils
import telemetry_handler

# flight controller variables
BLUE_RAVEN_PORTS = ["COM4"]
SIMULATE = True

# QR code variables
QR_PIXEL_SCALE = 2
QR_FRAMES_PER_CONTROLLER = 2

# runcam split v4 has a default aspect ratio of 4:3
# we can choose the resolution the program targets here
WIDTH = 2048
HEIGHT = 1536


def main():
    # connect to database
    db = db_handler.establish_db(False)

    # set all devices to inactive
    db_handler.reset_device_statuses(db)

    # begin telemetry streams
    if not SIMULATE:
        # get raven IDs from telemetry search
        raven_ids = telemetry_handler.start_raven_streams(db, BLUE_RAVEN_PORTS)
    else:
        # create raven simulations
        raven_ids = telemetry_handler.simulate_raven_streams(db, 2,
                                                             [
                                                                 './simulations/static-simulation.dat',
                                                                 './simulations/flight-simulation.dat'
                                                             ])

    # establish video feed
    video_stream = cv2.VideoCapture(1)

    # set width of video capture
    video_stream.set(cv2.CAP_PROP_FRAME_WIDTH, WIDTH)

    # set height of video capture
    video_stream.set(cv2.CAP_PROP_FRAME_HEIGHT, HEIGHT)

    # create empty QR code
    qr = qrcode.main.QRCode(
        version=13,  # force QR code scale
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # best error correction (up to 30%)
        box_size=QR_PIXEL_SCALE,  # set pixels for each module of QR code
        border=0,  # set QR code border
    )

    # set framerate tracking
    frames_in_last_second = 0
    frames_this_second = 0
    last_sample_time = time.time()

    frames_since_controller_swap = 0

    current_raven_index = 0

    # begin video loop
    while True:
        # load in a frame
        s, frame = video_stream.read()

        # skip failed frames
        if frame is None:
            continue

        # get telemetry data for this offset
        telemetry = telemetry_handler.get_telemetry(db, raven_ids[current_raven_index])

        # append fps count to telemetry
        telemetry.append(frames_in_last_second)

        # clear QR code data
        qr.clear()

        # add data to QR code
        qr.add_data(json.dumps(telemetry))

        # make qr code
        qr.make()

        # build QR image
        qr_img = qr.make_image()

        # get qr code image as numpy array
        qr_img = np.array(qr_img, dtype=np.uint8) * 255

        # cast color scale
        qr_img = cv2.cvtColor(qr_img, cv2.COLOR_GRAY2BGR)

        # add qr code
        frame = overlay_utils.handle_qr_border("write", frame, qr_img, QR_PIXEL_SCALE, 10)

        # show overlayed video
        cv2.imshow("output video", frame)
        cv2.waitKey(1)

        # check if a second has elapsed
        if int(time.time() - last_sample_time) >= 1:
            # set last seconds frames equal to this second
            frames_in_last_second = frames_this_second
            # reset frame count
            frames_this_second = 0
            # update sample time
            last_sample_time = time.time()

        # update frame counter
        frames_this_second += 1

        # increment frames since the controller index changed
        frames_since_controller_swap += 1

        # check if the controller index needs to change
        if frames_since_controller_swap == QR_FRAMES_PER_CONTROLLER:
            # reset frames since controller swap
            frames_since_controller_swap = 0

            # increase index counter
            current_raven_index += 1

            # reset index if needed
            if current_raven_index == len(raven_ids):
                current_raven_index = 0


if __name__ == "__main__":
    main()
