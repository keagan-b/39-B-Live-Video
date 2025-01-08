# Developed By Keagan Bowman
# Captures data sent by the transmitter server and decodes it.
# Data can either be displayed with TKinter, or added to a database
#
# receiver_server.py

import cv2
import json
import utils
import qrcode
import models
import tkinter
import numpy as np
import overlay_utils
from pyzbar import pyzbar
from PIL import Image, ImageTk

# load config
config = models.Config('./config.json')

# global variables
QR: qrcode.main.QRCode = None
VIDEO_STREAM: cv2.VideoCapture = None
OUTPUT_WRITER: cv2.VideoWriter = None
IMAGE_LABEL: tkinter.Label = None
CONTROLLER_UIs: list[models.ControllerUIObject] = []
ID_TO_CONTROLLER: dict[int, models.ControllerUIObject] = {}


def main():
    global QR, VIDEO_STREAM, OUTPUT_WRITER, IMAGE_LABEL, CONTROLLER_UIs

    # create QR object
    QR = qrcode.main.QRCode(
        version=13,  # force QR code scale
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # best error correction (up to 30%)
        box_size=config.QR_PIXEL_SCALE,  # set pixels for each module of QR code
        border=0,  # set QR code border
    )

    # get video stream
    VIDEO_STREAM = utils.establish_video_feed(config)

    # open video writer
    OUTPUT_WRITER = utils.create_video_writer(config)

    # === UI ===

    # create ui root
    root = tkinter.Tk()
    root.title("39-B Receiver System")

    # create image label
    image_label = tkinter.Label(root)

    # set default all-black image
    update_image(image_label, np.zeros((config.HEIGHT, config.WIDTH, 3), dtype=np.uint8))

    image_label.grid(row=0, column=0, rowspan=6, columnspan=len(config.BLUE_RAVEN_PORTS) * 4)
    IMAGE_LABEL = image_label

    # populate controller UI list
    for i in range(len(config.BLUE_RAVEN_PORTS)):
        # create object
        ui_obj = models.ControllerUIObject(f"Controller #{i + 1}", root)

        ui_obj.frame.grid(row=6, column=4 * i)

        CONTROLLER_UIs.append(ui_obj)

    # start UI update loop
    update_ui(root)

    root.mainloop()


def update_ui(root: tkinter.Tk):
    # load in a frame
    s, frame = VIDEO_STREAM.read()

    # ensure frame was loaded
    if frame is not None:
        # save frame to file
        OUTPUT_WRITER.write(frame)

        # update UI
        update_image(IMAGE_LABEL, frame)

        # clear QR code data
        QR.clear()

        # make qr code
        QR.make()

        # build QR image
        qr_img = QR.make_image()

        # get qr code image as numpy array
        qr_img = np.array(qr_img, dtype=np.uint8) * 255

        # cast color scale
        qr_img = cv2.cvtColor(qr_img, cv2.COLOR_GRAY2BGR)

        # read in QR code
        qr = overlay_utils.handle_overlay_request(config, "read", frame, qr_img)

        # decode data from QR
        decoded = pyzbar.decode(qr)

        # ensure decoded objects exist
        if len(decoded) > 0:
            # decode bytes & load as JSON
            data = json.loads([0].data.decode('utf-8'))

            # attempt to assign to controller
            try:
                # update controller with ID
                ID_TO_CONTROLLER[data[0]].update_variables(data)
            except KeyError:
                try:
                    # set new ID for controller if one doesn't exist
                    controller_ui = CONTROLLER_UIs.pop(0)
                    ID_TO_CONTROLLER[data[0]] = controller_ui

                    controller_ui.update_variables(data)
                except IndexError:
                    raise "Too many controllers active"

    # schedule next update
    root.after(50, update_ui, root)


def update_image(label: tkinter.Label, frame: np.ndarray) -> None:
    """
    Updates the image of a label
    :param label: Label to update
    :param frame: cv2 frame to update to
    :return: None
    """
    # load into PIL from array
    image = Image.fromarray(frame)
    new_image = ImageTk.PhotoImage(image)

    # update image
    label.config(image=new_image)
    label.image = new_image


if __name__ == "__main__":
    main()
