# Developed By Keagan Bowman
# Program for transcribing live video data from a camera and telemetry from two Blue Raven flight controllers
# into a single video for transmission using RPI GPIO headers to a radio video transmitter
#
# transmitter_server.py
from __future__ import annotations

import cv2
import json
import time
import utils
import models
import qrcode
import os.path
import datetime
import db_handler
import numpy as np
import overlay_utils
import telemetry_handler


def main():
    # load config
    config = models.Config('./config.json')

    # connect to database
    db = db_handler.establish_db(False)

    # set all devices to inactive
    db_handler.reset_device_statuses(db)

    # begin telemetry streams
    if not config.SIMULATE:
        # get raven IDs from telemetry search
        raven_ids = telemetry_handler.start_raven_streams(db, config.BLUE_RAVEN_PORTS)
    else:
        # create raven simulations
        raven_ids = telemetry_handler.simulate_raven_streams(db, 2,
                                                             [
                                                                 './simulations/static-simulation.dat',
                                                                 './simulations/flight-simulation.dat'
                                                             ])

    # establish video feed
    video_stream = utils.establish_video_feed(config)

    # establish output writer
    output_writer = utils.create_video_writer(config)

    # create empty QR code
    qr = qrcode.main.QRCode(
        version=13,  # force QR code scale
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # best error correction (up to 30%)
        box_size=config.QR_PIXEL_SCALE,  # set pixels for each module of QR code
        border=0,  # set QR code border
    )

    # set framerate tracking
    frames_in_last_second = 0
    frames_this_second = 0
    last_sample_time = time.time()

    frames_since_controller_swap = 0

    current_raven_index = 0

    # set transmission id counter
    transmission_id = 0

    # create viewport window
    cv2.namedWindow("outputVideo", cv2.WINDOW_NORMAL)

    # fullscreen window
    cv2.setWindowProperty("outputVideo", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

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

        # add transmission id to telemetry
        telemetry.append(transmission_id)

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
        frame = overlay_utils.handle_overlay_request(config, "write", frame, qr_img)

        # write frame to video file
        output_writer.write(frame)

        # show overlaid video
        cv2.imshow("outputVideo", frame)
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

        # increment transmission id
        transmission_id += 1

        # check if the controller index needs to change
        if frames_since_controller_swap == config.QR_FRAMES_PER_CONTROLLER:
            # reset frames since controller swap
            frames_since_controller_swap = 0

            # increase index counter
            current_raven_index += 1

            # reset index if needed
            if current_raven_index == len(raven_ids):
                current_raven_index = 0


if __name__ == "__main__":
    main()
