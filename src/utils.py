# Developed By Keagan Bowman
# Utility scripts for use in both transmission and receiving
#
# utils.py
from __future__ import annotations

import os
import cv2
import models
import datetime


def establish_video_feed(config: models.Config, priority_list=None) -> cv2.VideoCapture | None:
    """
    Attempts to create a VideoCapture object linked to the first camera it can find
    :param config: Configuration to pull resolution information from
    :param priority_list: A list of indexes to prioritize while checking for camera
    :return: VideCapture object of discovered camera, or None if no camera was found
    """

    # create empty list if no list is specified
    if priority_list is None:
        priority_list = []

    # append more possible indexes to the list (0-9)
    for i in range(0, 10):
        # add index if it doesn't exist in the priority list
        if i not in priority_list:
            priority_list.append(i)

    # check all indexes in the priority list
    for index in priority_list:
        # create VideoCapture stream
        camera_stream = cv2.VideoCapture(index)

        # check if camera is opened
        if camera_stream.isOpened():
            # set width of video capture
            camera_stream.set(cv2.CAP_PROP_FRAME_WIDTH, config.WIDTH)

            # set height of video capture
            camera_stream.set(cv2.CAP_PROP_FRAME_HEIGHT, config.HEIGHT)

            # return camera stream
            return camera_stream
    else:
        # no cameras found, raise error
        raise "No valid camera device found."


def create_video_writer(config: models.Config) -> cv2.VideoWriter:
    """
    Create a video writer using the config resolution
    :param config: Config object to get resolution from
    :return: cv2 VideoWriter object
    """
    # check if video-out directory exists
    if not os.path.exists("./video-out/"):
        # create directory
        os.mkdir("./video-out/")

    # create video name from current time
    video_name = datetime.datetime.now().strftime("%m-%d-%Y-%H-%M-%S")

    # specify codec
    cc = cv2.VideoWriter_fourcc(*config.OUTPUT_CODEC)

    # open video output
    output_writer = cv2.VideoWriter("./video-out/" + video_name + config.OUTPUT_EXTENSION, cc, 10,
                                    (config.WIDTH, config.HEIGHT))

    return output_writer
