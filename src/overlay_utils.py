# Developed By Keagan Bowman
# Utilities for handling overlaying videos/text onto a cv2 capture frame
#
# overlay_utils.py
from __future__ import annotations

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
        return handle_qr_border(mode, frame, qr, config.QR_PIXEL_SCALE, config.QR_BUFFER_SIZE)
    elif config.QR_MODE == 'bars':
        return handle_qr_bars(mode, frame, qr, config.QR_PIXEL_SCALE, config.QR_BUFFER_SIZE)
    elif config.QR_MODE == 'quadrants':
        return handle_qr_quadrants(mode, frame, qr, config.QR_BUFFER_SIZE)
    elif config.QR_MODE == 'overlay':
        return handle_qr_overlay(mode, frame, qr, config.QR_OVERLAY_X, config.QR_OVERLAY_Y)
    else:
        raise f"Unknown QR overlay mode '{config.QR_MODE}'."


def handle_qr_border(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, pixel_scale: int,
                     buffer_size: int = 0) -> np.ndarray:
    """
    Takes a qr code (or other image) and converts it to a border for another image
    :param mode: read from qr border or write to qr border?
    :param frame: image to overlay onto or read from
    :param qr: qr code (or other image) to overlay or fill
    :param pixel_scale: size of each qr module
    :param buffer_size: number of pixels that the QR code is padded with
    :return: a np.ndarray with the updated frame or QR code
    """
    # set cycles
    completed_cycles = 0

    # declare current x/y
    current_x = buffer_size
    current_y = buffer_size

    # determine max x/y
    max_x = frame.shape[1] - buffer_size
    max_y = frame.shape[0] - buffer_size

    # set current travel direction
    direction = "r"

    y = 0
    while y < qr.shape[1]:
        x = 0
        while x < qr.shape[0]:
            try:
                if mode == "read":
                    # read pixel from frame
                    qr[y:y + pixel_scale, x:x + pixel_scale] = frame[current_y:current_y + pixel_scale,
                                                               current_x:current_x + pixel_scale]
                else:
                    # set pixels in frame
                    frame[current_y:current_y + pixel_scale, current_x:current_x + pixel_scale] = qr[y:y + pixel_scale,
                                                                                                  x:x + pixel_scale]
                # increment x on successful replacement
                x += pixel_scale
            except ValueError:
                pass

            # determine next direction adjustment
            if direction == "r":
                # increase x by pixel scale
                current_x += pixel_scale
            elif direction == "d":
                # increase y by pixel scale
                current_y += pixel_scale
            elif direction == "l":
                # decrease x by pixel scale
                current_x -= pixel_scale
            elif direction == "u":
                # decrease y by pixel scale
                current_y -= pixel_scale

            offset = completed_cycles * pixel_scale

            # next x exceeds max x boundary
            if current_x + pixel_scale > max_x - offset and direction == "r":
                direction = "d"
            elif current_y + pixel_scale > max_y - offset and direction == "d":
                direction = "l"
            elif current_x - pixel_scale < offset + buffer_size and direction == "l":
                direction = "u"
            elif current_y - pixel_scale < offset + pixel_scale + buffer_size and direction == "u":
                direction = "r"
                completed_cycles += 1

        # increment y
        y += pixel_scale

    if mode == "read":
        return qr
    else:
        return frame


def handle_qr_bars(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, pixel_scale: int,
                   buffer_size: int = 0) -> np.ndarray | tuple[np.ndarray, np.ndarray]:
    """
    Applies a QR code overlay as a "bar" shape on the left side of a frame
    :param mode: read from qr border or write to qr border?
    :param frame: image to overlay border onto
    :param qr: qr code (or other image) to overlay
    :param pixel_scale: size of each qr module
    :param buffer_size: size of buffer to pad the QR code with
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
    current_x = buffer_size
    current_y = buffer_size

    # declare max values
    max_x = frame.shape[1] - buffer_size
    max_y = frame.shape[0] - buffer_size

    y = 0
    while y < qr.shape[0]:
        x = 0
        while x < qr.shape[1]:
            # update left pixels
            try:
                if mode == "read":
                    # read from left bar
                    qr_left[y:y + pixel_scale, x:x + pixel_scale] = frame[current_y:current_y + pixel_scale,
                                                                    current_x:current_x + pixel_scale]
                    # read from right bar
                    qr_right[y:y + pixel_scale, x:x + pixel_scale] = frame[current_y:current_y + pixel_scale,
                                                                     max_x - current_x - pixel_scale:max_x - current_x]
                else:
                    # write to left side of frame
                    frame[current_y:current_y + pixel_scale, current_x:current_x + pixel_scale] = qr[y:y + pixel_scale,
                                                                                                  x:x + pixel_scale]
                    # write to right side of frame
                    frame[current_y:current_y + pixel_scale, max_x - current_x - pixel_scale:max_x - current_x] = qr[
                                                                                                                  y:y + pixel_scale,
                                                                                                                  x:x + pixel_scale]

                # increment x on successful place
                x += pixel_scale
            except ValueError:
                pass

            # increase x
            current_y += pixel_scale

            # ensure the qr code is still within bounds
            if current_y >= max_y:
                # increase x
                current_x += pixel_scale
                # reset y
                current_y = buffer_size

        # increment y
        y += pixel_scale

    if mode == "read":
        # return read qr codes
        return qr_left, qr_right
    else:
        return frame


def handle_qr_quadrants(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray,
                        buffer_size: int = 0) -> np.ndarray:
    """
    Split a QR code into 4 quadrants and place in the corners of the frame, or read from a slit QR code
    :param mode: read or write QR code?
    :param frame: frame to read from / overlay onto
    :param qr: QR code to read to or write from
    :param buffer_size: padding for pushing the quadrants in
    :return:
    """
    # define max sizes
    max_x = frame.shape[1] - buffer_size
    max_y = frame.shape[0] - buffer_size

    # calculate quadrant size
    quadrant_size = math.ceil(qr.shape[0] / 2)

    if mode == "read":
        # read from top left
        qr[0:quadrant_size, 0:quadrant_size] = frame[buffer_size:buffer_size + quadrant_size,
                                               buffer_size:buffer_size + quadrant_size]

        # read from top right
        qr[0:quadrant_size, quadrant_size:] = frame[buffer_size:buffer_size + quadrant_size,
                                              max_x - buffer_size - quadrant_size:max_x - buffer_size]

        # read from bottom left
        qr[quadrant_size:, 0:quadrant_size] = frame[max_y - buffer_size - quadrant_size:max_y - buffer_size,
                                              buffer_size:buffer_size + quadrant_size]

        # read from bottom right
        qr[quadrant_size:, quadrant_size:] = frame[max_y - buffer_size - quadrant_size:max_y - buffer_size,
                                             max_x - buffer_size - quadrant_size:max_x - buffer_size]
    else:
        # write to top left
        frame[buffer_size:buffer_size + quadrant_size, buffer_size:buffer_size + quadrant_size] = qr[0:quadrant_size,
                                                                                                  0:quadrant_size]

        # write to top right
        frame[buffer_size:buffer_size + quadrant_size, max_x - buffer_size - quadrant_size:max_x - buffer_size] = qr[
                                                                                                                  0:quadrant_size,
                                                                                                                  quadrant_size:]

        # write to bottom left
        frame[max_y - buffer_size - quadrant_size:max_y - buffer_size, buffer_size:buffer_size + quadrant_size] = qr[
                                                                                                                  quadrant_size:,
                                                                                                                  0:quadrant_size]

        # write to bottom right
        frame[max_y - buffer_size - quadrant_size:max_y - buffer_size,
        max_x - buffer_size - quadrant_size:max_x - buffer_size] = qr[quadrant_size:, quadrant_size:]

    # determine return value based on mode
    if mode == "read":
        return qr
    else:
        return frame


def handle_qr_overlay(mode: Literal["read", "write"], frame: np.ndarray, qr: np.ndarray, x: int = 0, y: int = 0) -> np.ndarray:
    """
    Overlay a QR code onto a point ona  frame
    :param mode: read from qr border or write to qr border?
    :param frame: Frame to overlay QR onto or read QR from
    :param qr: Qr to overlay onto frame or to read into
    :param x: the x offset to place the QR at / read from
    :param y: the y offset to place the QR at / read from
    :return: The overlaid QR code or the read QR code
    """
    if mode == "read":
        # read QR code
        qr = frame[y:qr.shape[0] + y, x:qr.shape[1] + x]
    else:
        # overlay QR code
        frame[y:qr.shape[0] + y, x:qr.shape[1] + x] = qr

    if mode == "read":
        return qr
    else:
        return frame
