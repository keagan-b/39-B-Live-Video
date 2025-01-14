# Developed By Keagan Bowman
# Utilities for handling overlaying videos/text onto a cv2 capture frame
#
# overlay_utils.py
from __future__ import annotations

import cv2
import math
import copy
import models
import numpy as np
from typing import Literal


def handle_overlay_request(config: models.Config, mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray):
    """
    :param config: a config object containing relevant QR information
    :param mode: specify read/write mode
    :param frame: frame to overlay / read from
    :param qr: QR code to overlay / write to
    :return: Read mode - compiled QR;  Write mode - overlayed frame; None if unknown QR type
    """
    # ensure mode is valid
    if mode not in ["read", "write"]:
        raise AttributeError(f"Invalid mode '{mode}'.")

    # handle each type of QR overlay
    if config.QR_MODE == 'border':
        return handle_qr_border(mode, frame, qr, config)
    elif config.QR_MODE == 'bars':
        return handle_qr_bars(mode, frame, qr, config)
    elif config.QR_MODE == 'quadrants':
        return handle_qr_quadrants(mode, frame, qr, config)
    elif config.QR_MODE == 'overlay':
        return handle_qr_overlay(mode, frame, qr, config)
    else:
        raise f"Unknown QR overlay mode '{config.QR_MODE}'."


def handle_qr_border(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, config: models.Config) -> np.ndarray | None:
    """
    Takes a qr code (or other image) and converts it to a border for another image
    :param mode: read from qr border or write to qr border?
    :param frame: image to overlay onto or read from
    :param qr: qr code (or other image) to overlay or fill
    :param config: Configuration to use for qr overlay options
    :return: a np.ndarray with the updated frame or QR code
    """
    # set cycles
    completed_cycles = 0

    # declare current x/y
    current_x = config.QR_BUFFER_SIZE_LEFT
    current_y = config.QR_BUFFER_SIZE_TOP

    # determine max x/y
    max_x = frame.shape[1] - config.QR_BUFFER_SIZE_RIGHT
    max_y = frame.shape[0] - config.QR_BUFFER_SIZE_BOTTOM

    # set current travel direction
    direction = "r"

    y = 0
    while y < qr.shape[1]:
        x = 0
        while x < qr.shape[0]:
            try:
                if mode == "read":
                    # read pixel from frame
                    qr[y:y + config.QR_PIXEL_SCALE, x:x + config.QR_PIXEL_SCALE] = frame[current_y:current_y + config.QR_PIXEL_SCALE, current_x:current_x + config.QR_PIXEL_SCALE]
                else:
                    # set pixels in frame
                    frame[current_y:current_y + config.QR_PIXEL_SCALE, current_x:current_x + config.QR_PIXEL_SCALE] = qr[y:y + config.QR_PIXEL_SCALE, x:x + config.QR_PIXEL_SCALE]
                # increment x on successful replacement
                x += config.QR_PIXEL_SCALE
            except ValueError:
                return None

            # determine next direction adjustment
            if direction == "r":
                # increase x by pixel scale
                current_x += config.QR_PIXEL_SCALE
            elif direction == "d":
                # increase y by pixel scale
                current_y += config.QR_PIXEL_SCALE
            elif direction == "l":
                # decrease x by pixel scale
                current_x -= config.QR_PIXEL_SCALE
            elif direction == "u":
                # decrease y by pixel scale
                current_y -= config.QR_PIXEL_SCALE

            offset = completed_cycles * config.QR_PIXEL_SCALE

            # next x exceeds max x boundary
            if current_x + config.QR_PIXEL_SCALE > max_x - offset and direction == "r":
                direction = "d"
            elif current_y + config.QR_PIXEL_SCALE > max_y - offset and direction == "d":
                direction = "l"
            elif current_x - config.QR_PIXEL_SCALE < offset + config.QR_BUFFER_SIZE_LEFT and direction == "l":
                direction = "u"
            elif current_y - config.QR_PIXEL_SCALE < offset + config.QR_PIXEL_SCALE + config.QR_BUFFER_SIZE_TOP and direction == "u":
                direction = "r"
                completed_cycles += 1

        # increment y
        y += config.QR_PIXEL_SCALE

    if mode == "read":
        return qr
    else:
        return frame


def handle_qr_bars(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, config: models.Config) -> np.ndarray | tuple[np.ndarray, np.ndarray] | tuple[None, None]:
    """
    Applies a QR code overlay as a "bar" shape on the left side of a frame
    :param mode: read from qr border or write to qr border?
    :param frame: image to overlay border onto
    :param qr: qr code (or other image) to overlay
    :param config: Configuration to use for qr overlay options
    :return: The frame with the applied QR code, or the read QR codes from both sides
    """
    qr_left = None
    qr_right = None

    if mode == "read":
        # deep copy qr for left
        qr_left = copy.deepcopy(qr)
        # set right qr
        qr_right = qr

    # declare current x/y
    min_x = config.QR_BUFFER_SIZE_LEFT
    current_y = config.QR_BUFFER_SIZE_TOP

    # determine max x/y
    max_x = frame.shape[1] - config.QR_BUFFER_SIZE_RIGHT
    max_y = frame.shape[0] - config.QR_BUFFER_SIZE_BOTTOM

    current_x = config.QR_PIXEL_SCALE

    y = 0
    while y < qr.shape[0]:
        x = 0
        while x < qr.shape[1]:
            # update left pixels
            try:
                if mode == "read":
                    # read from left bar
                    qr_left[y:y + config.QR_PIXEL_SCALE, x:x + config.QR_PIXEL_SCALE] = frame[current_y:current_y + config.QR_PIXEL_SCALE, min_x + current_x:min_x + current_x + config.QR_PIXEL_SCALE]
                    # read from right bar
                    qr_right[y:y + config.QR_PIXEL_SCALE, x:x + config.QR_PIXEL_SCALE] = frame[current_y:current_y + config.QR_PIXEL_SCALE, max_x - current_x - config.QR_PIXEL_SCALE:max_x - current_x]
                else:
                    # write to left side of frame
                    frame[current_y:current_y + config.QR_PIXEL_SCALE, min_x + current_x:min_x + current_x + config.QR_PIXEL_SCALE] = qr[y:y + config.QR_PIXEL_SCALE, x:x + config.QR_PIXEL_SCALE]
                    # write to right side of frame
                    frame[current_y:current_y + config.QR_PIXEL_SCALE, max_x - current_x - config.QR_PIXEL_SCALE:max_x - current_x] = qr[y:y + config.QR_PIXEL_SCALE, x:x + config.QR_PIXEL_SCALE]

                # increment x on successful place
                x += config.QR_PIXEL_SCALE
            except ValueError:
                return None, None

            # increase x
            current_y += config.QR_PIXEL_SCALE

            # ensure the qr code is still within bounds
            if current_y >= max_y:
                # increase x
                current_x += config.QR_PIXEL_SCALE
                # reset y
                current_y = config.QR_BUFFER_SIZE_TOP

        # increment y
        y += config.QR_PIXEL_SCALE

    if mode == "read":
        # return read qr codes
        return qr_left, qr_right
    else:
        return frame


def handle_qr_quadrants(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, config: models.Config) -> np.ndarray:
    """
    Split a QR code into 4 quadrants and place in the corners of the frame, or read from a slit QR code
    :param mode: read or write QR code?
    :param frame: frame to read from / overlay onto
    :param qr: QR code to read to or write from
    :param config: Configuration to use for qr overlay options
    :return:
    """
    # determine max x/y
    max_x = frame.shape[1] - config.QR_BUFFER_SIZE_RIGHT
    max_y = frame.shape[0] - config.QR_BUFFER_SIZE_BOTTOM

    # calculate quadrant size
    quadrant_size = math.ceil(qr.shape[0] / 2)

    if mode == "read":
        # read from top left
        qr[0:quadrant_size, 0:quadrant_size] = frame[config.QR_BUFFER_SIZE_TOP:config.QR_BUFFER_SIZE_TOP + quadrant_size,
                                               config.QR_BUFFER_SIZE_LEFT:config.QR_BUFFER_SIZE_LEFT + quadrant_size]

        # read from top right
        qr[0:quadrant_size, quadrant_size:] = frame[config.QR_BUFFER_SIZE_TOP:config.QR_BUFFER_SIZE_TOP + quadrant_size,
                                              max_x - config.QR_BUFFER_SIZE_RIGHT - quadrant_size:max_x - config.QR_BUFFER_SIZE_RIGHT]

        # read from bottom left
        qr[quadrant_size:, 0:quadrant_size] = frame[max_y - config.QR_BUFFER_SIZE_BOTTOM - quadrant_size:max_y - config.QR_BUFFER_SIZE_BOTTOM,
                                              config.QR_BUFFER_SIZE_LEFT:config.QR_BUFFER_SIZE_LEFT + quadrant_size]

        # read from bottom right
        qr[quadrant_size:, quadrant_size:] = frame[max_y - config.QR_BUFFER_SIZE_BOTTOM - quadrant_size:max_y - config.QR_BUFFER_SIZE_BOTTOM,
                                             max_x - config.QR_BUFFER_SIZE_RIGHT - quadrant_size:max_x - config.QR_BUFFER_SIZE_RIGHT]
    else:
        # write to top left
        frame[config.QR_BUFFER_SIZE_TOP:config.QR_BUFFER_SIZE_TOP + quadrant_size, config.QR_BUFFER_SIZE_LEFT:config.QR_BUFFER_SIZE_LEFT + quadrant_size] = qr[0:quadrant_size,
                                                                                                  0:quadrant_size]

        # write to top right
        frame[config.QR_BUFFER_SIZE_TOP:config.QR_BUFFER_SIZE_TOP + quadrant_size, max_x - config.QR_BUFFER_SIZE_RIGHT - quadrant_size:max_x - config.QR_BUFFER_SIZE_RIGHT] = qr[
                                                                                                                  0:quadrant_size,
                                                                                                                  quadrant_size:]

        # write to bottom left
        frame[max_y - config.QR_BUFFER_SIZE_BOTTOM - quadrant_size:max_y - config.QR_BUFFER_SIZE_BOTTOM, config.QR_BUFFER_SIZE_LEFT:config.QR_BUFFER_SIZE_LEFT + quadrant_size] = qr[
                                                                                                                  quadrant_size:,
                                                                                                                  0:quadrant_size]

        # write to bottom right
        frame[max_y - config.QR_BUFFER_SIZE_BOTTOM - quadrant_size:max_y - config.QR_BUFFER_SIZE_BOTTOM,
        max_x - config.QR_BUFFER_SIZE_RIGHT - quadrant_size:max_x - config.QR_BUFFER_SIZE_RIGHT] = qr[quadrant_size:, quadrant_size:]

    # determine return value based on mode
    if mode == "read":
        return qr
    else:
        return frame


def handle_qr_overlay(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, config: models.Config) -> np.ndarray:
    """
    Overlay a QR code onto a point ona  frame
    :param mode: read from qr border or write to qr border?
    :param frame: Frame to overlay QR onto or read QR from
    :param qr: Qr to overlay onto frame or to read into
    :param config: Configuration to use for qr overlay options
    :return: The overlaid QR code or the read QR code
    """
    if mode == "read":
        # read QR code
        qr = frame[config.QR_OVERLAY_Y:qr.shape[0] + config.QR_OVERLAY_Y, config.QR_OVERLAY_X:qr.shape[1] + config.QR_OVERLAY_X]
    else:
        # overlay QR code
        frame[config.QR_OVERLAY_Y:qr.shape[0] + config.QR_OVERLAY_Y, config.QR_OVERLAY_X:qr.shape[1] + config.QR_OVERLAY_X] = qr

    if mode == "read":
        return qr
    else:
        return frame
