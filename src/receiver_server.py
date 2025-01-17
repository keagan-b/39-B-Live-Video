# Developed By Keagan Bowman
# Captures data sent by the transmitter server and decodes it.
# Data can either be displayed with TKinter, or added to a database
#
# receiver_server.py

# TODO
# add controller data to DB on receive

import cv2
import json
import utils
import qrcode
import models
import tkinter
import numpy as np
import overlay_utils
from tkinter import ttk
from pyzbar import pyzbar
from PIL import Image, ImageTk
from pyzbar.pyzbar import ZBarSymbol

# load config
config = models.Config('./config.json')

# global variables
QR: qrcode.main.QRCode = None
VIDEO_STREAM: cv2.VideoCapture = None
OUTPUT_WRITER: cv2.VideoWriter = None
IMAGE_LABEL: tkinter.Label = None
CALIBRATION_IMAGE_LABEL: tkinter.Label = None
CALIBRATION_QR_LABEL: tkinter.Label = None
CONTROLLER_UIs: list[models.ControllerUIObject] = []
ID_TO_CONTROLLER: dict[int, models.ControllerUIObject] = {}
DEVICE_ID_VAR: tkinter.StringVar = None


def main():
    global QR, VIDEO_STREAM, OUTPUT_WRITER, IMAGE_LABEL, CONTROLLER_UIs

    # create QR object
    QR = qrcode.main.QRCode(
        version=13,  # force QR code scale
        error_correction=qrcode.constants.ERROR_CORRECT_H,  # best error correction (up to 30%)
        box_size=config.QR_PIXEL_SCALE,  # set pixels for each module of QR code
        border=config.QR_BORDER_SIZE,  # set QR code border
    )

    # get video stream
    VIDEO_STREAM = utils.establish_video_feed(config)

    # open video writer
    OUTPUT_WRITER = utils.create_video_writer(config)

    # figure out number of controllers based on simulating or not
    num_controllers = len(config.BLUE_RAVEN_PORTS)

    if config.SIMULATE:
        num_controllers = config.SIMULATION_COUNT

    # === UI ===

    # create ui root
    root = tkinter.Tk()
    root.title("39-B Receiver System")

    receiver_panel = tkinter.Frame(root)

    # create image label
    image_label = tkinter.Label(receiver_panel)

    # set default all-black image
    update_image(image_label, np.zeros((config.HEIGHT, config.WIDTH, 3), dtype=np.uint8))

    image_label.grid(row=0, column=0, rowspan=6, columnspan=num_controllers * 4)
    IMAGE_LABEL = image_label

    # create calibration menu button
    calibration_menu_button = tkinter.Button(receiver_panel, text="Calibration Menu",
                                             command=lambda: create_calibration_menu(root, receiver_panel))
    calibration_menu_button.grid(row=6, column=int(num_controllers / 2))

    # populate controller UI list
    for i in range(num_controllers):
        # create object
        ui_obj = models.ControllerUIObject(f"Controller #{i + 1}", receiver_panel)

        ui_obj.frame.grid(row=7, column=4 * i)

        CONTROLLER_UIs.append(ui_obj)

    # start UI update loop
    update_ui(receiver_panel)

    receiver_panel.grid(row=0, column=0)

    root.mainloop()


def update_ui(root: tkinter.Frame):
    # load in a frame
    s, frame = VIDEO_STREAM.read()

    # ensure frame was loaded
    if frame is not None:
        # loop exactly once - allows us to quit the loop if an error is thrown
        # and then reschedule the update
        for i in range(1):
            # save frame to file
            OUTPUT_WRITER.write(frame)

            # apply zoom to frame
            try:
                frame = cv2.resize(frame, None, fx=config.WINDOW_ZOOM_X, fy=config.WINDOW_ZOOM_Y, interpolation=cv2.INTER_LINEAR)
            except cv2.error:
                pass

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
            qr_img = cv2.cvtColor(qr_img, cv2.COLOR_GRAY2RGB)

            # read in QR code
            try:
                qr = overlay_utils.handle_overlay_request(config, "read", frame, qr_img)
            except ValueError:
                break

            # cast back to grayscale
            try:
                qr = cv2.cvtColor(qr, cv2.COLOR_RGB2GRAY)
            except cv2.error:
                pass

            # decode data from QR
            decoded = pyzbar.decode(qr)

            # ensure decoded objects exist
            if len(decoded) > 0:
                # decode bytes & load as JSON
                try:
                    data = json.loads(decoded[0].data.decode('utf-8'))
                except json.JSONDecodeError:
                    break

                # attempt to assign to controller
                try:
                    # update controller with ID
                    try:
                        ID_TO_CONTROLLER[data[0]].update_variables(data)
                    except TypeError:
                        pass
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
    try:
        image = Image.fromarray(frame)
        new_image = ImageTk.PhotoImage(image)
    except AttributeError:
        return

    # update image
    label.config(image=new_image)
    label.image = new_image


def create_calibration_menu(root: tkinter.Tk, receiver_panel: tkinter.Frame):
    """
    Creates the calibration menu UI

    :param root: root tkinter frame to target
    :param receiver_panel: tkinter frame to disable
    :return:
    """
    global CALIBRATION_IMAGE_LABEL, CALIBRATION_QR_LABEL, DEVICE_ID_VAR

    calibration_panel = tkinter.Frame(root)

    # create UI
    image_label = tkinter.Label(calibration_panel)
    qr_label = tkinter.Label(calibration_panel)

    # qr read settings
    qr_mode_label = tkinter.Label(calibration_panel, text="QR Mode:")
    qr_mode_var = tkinter.StringVar(value=config.QR_MODE)
    qr_mode_select = ttk.Combobox(calibration_panel, values=['border', 'bars', 'quadrants', 'overlay'],
                                  textvariable=qr_mode_var)
    qr_mode_select.set(value=config.QR_MODE)

    qr_pixel_scale_label = tkinter.Label(calibration_panel, text="Pixel Scale:")
    qr_pixel_scale_var = tkinter.IntVar(value=config.QR_PIXEL_SCALE)
    qr_pixel_scale_entry = tkinter.Entry(calibration_panel, textvariable=qr_pixel_scale_var)

    qr_overlay_x_label = tkinter.Label(calibration_panel, text="Overlay X:")
    qr_overlay_x_var = tkinter.IntVar(value=config.QR_OVERLAY_X)
    qr_overlay_x_entry = tkinter.Entry(calibration_panel, textvariable=qr_overlay_x_var)

    qr_overlay_y_label = tkinter.Label(calibration_panel, text="Overlay Y:")
    qr_overlay_y_var = tkinter.IntVar(value=config.QR_OVERLAY_Y)
    qr_overlay_y_entry = tkinter.Entry(calibration_panel, textvariable=qr_overlay_y_var)

    qr_buffer_size_top_label = tkinter.Label(calibration_panel, text="Top Buffer:")
    qr_buffer_size_top_var = tkinter.IntVar(value=config.QR_BUFFER_SIZE_TOP)
    qr_buffer_size_top_entry = tkinter.Entry(calibration_panel, textvariable=qr_buffer_size_top_var)

    qr_buffer_size_bottom_label = tkinter.Label(calibration_panel, text="Bottom Buffer:")
    qr_buffer_size_bottom_var = tkinter.IntVar(value=config.QR_BUFFER_SIZE_BOTTOM)
    qr_buffer_size_bottom_entry = tkinter.Entry(calibration_panel, textvariable=qr_buffer_size_bottom_var)

    qr_buffer_size_left_label = tkinter.Label(calibration_panel, text="Left Buffer:")
    qr_buffer_size_left_var = tkinter.IntVar(value=config.QR_BUFFER_SIZE_LEFT)
    qr_buffer_size_left_entry = tkinter.Entry(calibration_panel, textvariable=qr_buffer_size_left_var)

    qr_buffer_size_right_label = tkinter.Label(calibration_panel, text="Right Buffer:")
    qr_buffer_size_right_var = tkinter.IntVar(value=config.QR_BUFFER_SIZE_RIGHT)
    qr_buffer_size_right_entry = tkinter.Entry(calibration_panel, textvariable=qr_buffer_size_right_var)

    qr_border_size_label = tkinter.Label(calibration_panel, text="Border Size:")
    qr_border_size_var = tkinter.IntVar(value=config.QR_BORDER_SIZE)
    qr_border_size_entry = tkinter.Entry(calibration_panel, textvariable=qr_border_size_var)

    window_zoom_x_label = tkinter.Label(calibration_panel, text="X Zoom:")
    window_zoom_x_var = tkinter.StringVar(value=config.WINDOW_ZOOM_X)
    window_zoom_x_entry = tkinter.Entry(calibration_panel, textvariable=window_zoom_x_var)

    window_zoom_y_label = tkinter.Label(calibration_panel, text="Y Zoom:")
    window_zoom_y_var = tkinter.StringVar(value=config.WINDOW_ZOOM_Y)
    window_zoom_y_entry = tkinter.Entry(calibration_panel, textvariable=window_zoom_y_var)

    # device id info
    device_id_label = tkinter.Label(calibration_panel, text="Device ID:")
    device_id_var = tkinter.StringVar()
    device_id_entry = tkinter.Entry(calibration_panel, state='disabled', textvariable=device_id_var)

    DEVICE_ID_VAR = device_id_var

    def close_panel():
        calibration_panel.grid_forget()
        calibration_panel.destroy()
        receiver_panel.grid(row=0, column=0)
        update_ui(receiver_panel)

    def save_config():
        config.save()
        close_panel()

    save_button = tkinter.Button(text="Save", command=save_config)
    cancel_button = tkinter.Button(text="Cancel", command=close_panel)

    # place objects
    image_label.grid(row=0, column=0, rowspan=4, columnspan=3)
    qr_label.grid(row=0, column=3, rowspan=2, columnspan=1)

    qr_mode_label.grid(row=5, column=0)
    qr_mode_select.grid(row=5, column=1)

    qr_pixel_scale_label.grid(row=6, column=0)
    qr_pixel_scale_entry.grid(row=6, column=1)

    qr_overlay_x_label.grid(row=5, column=2)
    qr_overlay_x_entry.grid(row=5, column=3)

    qr_overlay_y_label.grid(row=6, column=2)
    qr_overlay_y_entry.grid(row=6, column=3)

    qr_buffer_size_top_label.grid(row=7, column=0)
    qr_buffer_size_top_entry.grid(row=7, column=1)

    qr_buffer_size_bottom_label.grid(row=7, column=2)
    qr_buffer_size_bottom_entry.grid(row=7, column=3)

    qr_buffer_size_left_label.grid(row=8, column=0)
    qr_buffer_size_left_entry.grid(row=8, column=1)

    qr_buffer_size_right_label.grid(row=8, column=2)
    qr_buffer_size_right_entry.grid(row=8, column=3)

    window_zoom_x_label.grid(row=9, column=0)
    window_zoom_x_entry.grid(row=9, column=1)

    window_zoom_y_label.grid(row=9, column=2)
    window_zoom_y_entry.grid(row=9, column=3)

    qr_border_size_label.grid(row=10, column=0)
    qr_border_size_entry.grid(row=10, column=1)

    device_id_label.grid(row=10, column=2)
    device_id_entry.grid(row=10, column=3)

    save_button.grid(row=11, column=1)
    cancel_button.grid(row=11, column=2)

    def update_qr_mode(*_):
        config.QR_MODE = qr_mode_var.get()

    def update_qr_pixel_scale(*_):
        global QR

        if validate_input(qr_pixel_scale_var):
            config.QR_PIXEL_SCALE = qr_pixel_scale_var.get()

            QR = qrcode.main.QRCode(
                version=13,  # force QR code scale
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # best error correction (up to 30%)
                box_size=config.QR_PIXEL_SCALE,  # set pixels for each module of QR code
                border=config.QR_BORDER_SIZE,  # set QR code border
            )

    def update_qr_overlay_x(*_):
        if validate_input(qr_overlay_x_var):
            config.QR_OVERLAY_X = qr_overlay_x_var.get()

    def update_qr_overlay_y(*_):
        if validate_input(qr_overlay_y_var):
            config.QR_OVERLAY_Y = qr_overlay_y_var.get()

    def update_qr_buffer_size_top(*_):
        if validate_input(qr_buffer_size_top_var):
            config.QR_BUFFER_SIZE_TOP = qr_buffer_size_top_var.get()

    def update_qr_buffer_size_bottom(*_):
        if validate_input(qr_buffer_size_bottom_var):
            config.QR_BUFFER_SIZE_BOTTOM = qr_buffer_size_bottom_var.get()

    def update_qr_buffer_size_left(*_):
        if validate_input(qr_buffer_size_left_var):
            config.QR_BUFFER_SIZE_LEFT = qr_buffer_size_left_var.get()

    def update_qr_buffer_size_right(*_):
        if validate_input(qr_buffer_size_right_var):
            config.QR_BUFFER_SIZE_RIGHT = qr_buffer_size_right_var.get()

    def update_window_zoom_x(*_):
        try:
            config.WINDOW_ZOOM_X = float(window_zoom_x_var.get())
        except ValueError:
            pass

    def update_window_zoom_y(*_):
        try:
            config.WINDOW_ZOOM_Y = float(window_zoom_y_var.get())
        except ValueError:
            pass

    def update_qr_border_size(*_):
        global QR
        if validate_input(qr_border_size_var):
            config.QR_BORDER_SIZE = qr_border_size_var.get()

            QR = qrcode.main.QRCode(
                version=13,  # force QR code scale
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # best error correction (up to 30%)
                box_size=config.QR_PIXEL_SCALE,  # set pixels for each module of QR code
                border=config.QR_BORDER_SIZE,  # set QR code border
            )

    # bind events
    qr_mode_var.trace_add("write", update_qr_mode)
    qr_pixel_scale_var.trace_add("write", update_qr_pixel_scale)
    qr_overlay_x_var.trace_add("write", update_qr_overlay_x)
    qr_overlay_y_var.trace_add("write", update_qr_overlay_y)
    qr_buffer_size_top_var.trace_add("write", update_qr_buffer_size_top)
    qr_buffer_size_bottom_var.trace_add("write", update_qr_buffer_size_bottom)
    qr_buffer_size_left_var.trace_add("write", update_qr_buffer_size_left)
    qr_buffer_size_right_var.trace_add("write", update_qr_buffer_size_right)
    window_zoom_x_var.trace_add("write", update_window_zoom_x)
    window_zoom_y_var.trace_add("write", update_window_zoom_y)
    qr_border_size_var.trace_add("write", update_qr_border_size)

    # hide receiver ui
    receiver_panel.grid_forget()

    # place frame on UI
    calibration_panel.grid(row=0, column=0)

    # set global variables
    CALIBRATION_IMAGE_LABEL = image_label
    CALIBRATION_QR_LABEL = qr_label

    # start calibration update
    update_calibration_ui(calibration_panel)


def update_calibration_ui(panel: tkinter.Frame):
    global QR
    # load in frame
    s, frame = VIDEO_STREAM.read()

    # ensure frame was loaded
    if frame is not None:
        # loop exactly once - allows us to quit the loop if an error is thrown
        # and then reschedule the update
        for i in range(1):
            # apply zoom to frame
            try:
                frame = cv2.resize(frame, None, fx=config.WINDOW_ZOOM_X, fy=config.WINDOW_ZOOM_Y)
            except cv2.error:
                pass

            # clear QR code data
            QR.clear()

            # make qr code
            QR.make()

            # build QR image
            qr_img = QR.make_image()

            # get qr code image as numpy array
            qr_img = np.array(qr_img, dtype=np.uint8) * 255

            # generate calibration qr data
            calibration_qr = np.zeros(qr_img.shape, dtype=np.uint8)

            # convert to RGBA
            calibration_qr = cv2.cvtColor(calibration_qr, cv2.COLOR_RGB2RGBA)

            # set channels
            calibration_qr[:, :, 0] = 255  # red
            calibration_qr[:, :, 1] = 0  # green
            calibration_qr[:, :, 2] = 0  # blue
            calibration_qr[:, :, 3] = 255  # alpha

            # convert frame to RGBA
            calibration_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2RGBA)

            # generate calibration label image
            try:
                calibration_frame = overlay_utils.handle_overlay_request(config, "write", calibration_frame,
                                                                         calibration_qr)
            except ValueError:
                break

            # set calibration label image
            update_image(CALIBRATION_IMAGE_LABEL, calibration_frame)

            # cast color scale
            qr_img = cv2.cvtColor(qr_img, cv2.COLOR_GRAY2RGB)

            # read in QR code
            qr = overlay_utils.handle_overlay_request(config, "read", frame, qr_img)

            # cast back to grayscale
            try:
                qr = cv2.cvtColor(qr, cv2.COLOR_RGB2GRAY)
            except cv2.error:
                pass

            # decode data from QR
            try:
                decoded = pyzbar.decode(qr)
            except TypeError:
                decoded = []

            # ensure decoded objects exist
            if len(decoded) > 0:
                # decode bytes & load as JSON
                try:
                    data = json.loads(decoded[0].data.decode('utf-8'))

                    try:
                        DEVICE_ID_VAR.set(data[0])
                    except TypeError:
                        DEVICE_ID_VAR.set("No ID Found")
                except AttributeError:
                    DEVICE_ID_VAR.set("No ID Found")
            else:
                DEVICE_ID_VAR.set("No ID Found")

            # update qr image
            update_image(CALIBRATION_QR_LABEL, qr)

    # schedule next update
    panel.after(50, update_calibration_ui, panel)


def validate_input(inp: tkinter.IntVar):
    try:
        int(inp.get())
        return True
    except (ValueError, tkinter.TclError):
        return False


if __name__ == "__main__":
    main()
