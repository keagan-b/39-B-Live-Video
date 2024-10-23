# Developed By Keagan Bowman
# Program for transcribing live video data from a Runcam 4 v2 and telemetry from two Blue Raven flight controllers
# into a single video for transmission using RPI GPIO headers to a radio video transmitter
#
# main.py
from __future__ import annotations

import cv2
import time
import db_handler
import telemetry_handler

BLUE_RAVEN_PORTS = ["COM4"]
VIDEO_IN = ""
VIDEO_OUT = ""


def main():
    # connect to database
    db = db_handler.establish_db(True)

    # set all devices to inactive
    db_handler.reset_device_statuses(db)

    # begin telemetry streams
    raven_ids = telemetry_handler.start_raven_streams(db, BLUE_RAVEN_PORTS)

    # establish video feed
    video_stream = cv2.VideoCapture(0)

    # set framerate tracking
    frames_in_last_second = 0
    frames_this_second = 0
    last_sample_time = time.time()

    # begin video loop
    while True:
        # load in a frame
        s, frame = video_stream.read()

        # skip failed frames
        if frame is None:
            continue

        # get telemetry data
        telemetry = telemetry_handler.get_telemetry(db, raven_ids[0])

        # combine telemetry data and video feed
        i = 0
        for key in telemetry:
            # skip spacers in telemetry dict
            if telemetry[key] != "":
                # add text to image, starting in the top left
                cv2.putText(frame, f"{key}: {telemetry[key]}", (0, 30 * (i + 1)), cv2.FONT_HERSHEY_COMPLEX_SMALL, 1,
                            (0, 0, 255),
                            1)

            # increment offset
            i += 1

        # add FPS count to top right of screen
        cv2.putText(frame, f"FPS: {frames_in_last_second}", (frame.shape[1] - 100, 30), cv2.FONT_HERSHEY_COMPLEX_SMALL,
                    1,
                    (0, 0, 255),
                    1)

        cv2.imshow("output video", frame)
        cv2.waitKey(1)

        # transmit frame
        pass

        # check if a second has elapsed
        if int(time.time() - last_sample_time) >= 1:
            # set last seconds frames equal to this second
            frames_in_last_second = frames_this_second
            # reset frame count
            frames_this_second = 0
            # update sample time
            last_sample_time = time.time()
            print(f"FPS: {frames_in_last_second}")

        # update frame counter
        frames_this_second += 1


if __name__ == "__main__":
    main()
