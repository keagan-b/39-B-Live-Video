# Developed By Keagan Bowman
# Utility models for universal use
#
# models.py

import json
import os.path
import tkinter


class Config:
    # create a list of default config values
    _config_path = ''

    # loading the config
    def __init__(self, config_path: str):
        # set default values

        # QR code variables
        self.QR_MODE: str = 'border'
        self.QR_PIXEL_SCALE: int = 2
        self.QR_FRAMES_PER_CONTROLLER: int = 2
        self.QR_BUFFER_SIZE: int = 10
        self.QR_OVERLAY_X: int = 0
        self.QR_OVERLAY_Y: int = 0

        # Specified target resolution for transmitter output
        self.WIDTH: int = 720
        self.HEIGHT: int = 576

        # misc
        # flight controller variables
        self.BLUE_RAVEN_PORTS = ["COM4"]
        self.SIMULATE = True

        # specify local video output codec
        # valid codecs include:
        # "FFV1" - lossless - .avi, .mkv
        # "XVID" - H.264 - .avi
        # "MJPG" - jpeg frames - .avi
        self.OUTPUT_CODEC = "XVID"

        # video file output extension - please correlate with above
        self.OUTPUT_EXTENSION = ".avi"

        self._config_path = config_path

        self.load()

    def load(self):
        # check if config path exists
        if os.path.exists(self._config_path):
            # load config
            with open(self._config_path, "r") as f:
                try:
                    config_data = json.load(f)
                except json.JSONDecodeError:
                    self.save()
                    self.load()

            # set values loaded from config
            try:
                self.QR_MODE = config_data['QR_MODE']
                self.QR_PIXEL_SCALE = config_data['QR_PIXEL_SCALE']
                self.QR_FRAMES_PER_CONTROLLER = config_data['QR_FRAMES_PER_CONTROLLER']
                self.QR_BUFFER_SIZE = config_data['QR_BUFFER_SIZE']
                self.QR_OVERLAY_X = config_data['QR_OVERLAY_X']
                self.QR_OVERLAY_Y = config_data['QR_OVERLAY_Y']

                self.WIDTH = config_data['WIDTH']
                self.HEIGHT = config_data['HEIGHT']

                self.BLUE_RAVEN_PORTS = config_data['BLUE_RAVEN_PORTS']
                self.SIMULATE = config_data['SIMULATE']
                self.OUTPUT_CODEC = config_data['OUTPUT_CODEC']
                self.OUTPUT_EXTENSION = config_data['OUTPUT_EXTENSION']
            except KeyError:
                # value not found - save and reload
                print("Config is broken, adding missing variables...")
                self.save()
                self.load()

    def save(self):
        # open config location
        with open(self._config_path, "w") as f:
            # save config using ConfigEncoder
            json.dump(self, f, cls=ConfigEncoder, indent=4)


# custom JSON encoder for Config object
class ConfigEncoder(json.JSONEncoder):
    def default(self, obj):
        # ensure object matches Config
        if isinstance(obj, Config):
            # return list of variables
            return {k: v for k, v in vars(obj).items() if not k.startswith('_')}

        # use default behavior
        return super().default(obj)


class ControllerUIObject:
    def __init__(self, controller_name: str, root: tkinter.Tk):
        # create frame
        self.frame = tkinter.Frame(root)

        # create controller label
        self._controller_name_label = tkinter.Label(self.frame, text=controller_name)

        # create acceleration labels
        self.acceleration_x_var = tkinter.StringVar(self.frame)
        self.acceleration_y_var = tkinter.StringVar(self.frame)
        self.acceleration_z_var = tkinter.StringVar(self.frame)

        self._acceleration_label = tkinter.Label(self.frame, text="Acceleration:")
        self._acceleration_x_entry = tkinter.Entry(self.frame, textvariable=self.acceleration_x_var, state='disabled')
        self._acceleration_y_entry = tkinter.Entry(self.frame, textvariable=self.acceleration_y_var, state='disabled')
        self._acceleration_z_entry = tkinter.Entry(self.frame, textvariable=self.acceleration_z_var, state='disabled')

        # create velocity label
        self.velocity_var = tkinter.StringVar(self.frame)
        self._velocity_label = tkinter.Label(self.frame, text="Velocity:")
        self._velocity_entry = tkinter.Entry(self.frame, textvariable=self.velocity_var, state='disabled')

        # create altitude label
        self.altitude_var = tkinter.StringVar(self.frame)
        self._altitude_label = tkinter.Label(self.frame, text="Altitude:")
        self._altitude_entry = tkinter.Entry(self.frame, textvariable=self.altitude_var, state='disabled')

        # create tilt label
        self.tilt_var = tkinter.StringVar(self.frame)
        self._tilt_label = tkinter.Label(self.frame, text="Tilt:")
        self._tilt_entry = tkinter.Entry(self.frame, textvariable=self.tilt_var, state='disabled')

        # create roll label
        self.roll_var = tkinter.StringVar(self.frame)
        self._roll_label = tkinter.Label(self.frame, text="Roll:")
        self._roll_entry = tkinter.Entry(self.frame, textvariable=self.roll_var, state='disabled')

        # create battery label
        self.battery_var = tkinter.StringVar(self.frame)
        self._battery_label = tkinter.Label(self.frame, text="Battery:")
        self._battery_entry = tkinter.Entry(self.frame, textvariable=self.battery_var, state='disabled')

        # create temperature label
        self.temp_var = tkinter.StringVar(self.frame)
        self._temp_label = tkinter.Label(self.frame, text="Temperature:")
        self._temp_entry = tkinter.Entry(self.frame, textvariable=self.temp_var, state='disabled')

        # arrange UI elements

        # controller name
        self._controller_name_label.grid(row=0, column=0)

        # acceleration
        self._acceleration_label.grid(row=1, column=0)
        self._acceleration_x_entry.grid(row=1, column=1)
        self._acceleration_y_entry.grid(row=1, column=2)
        self._acceleration_z_entry.grid(row=1, column=3)

        # velocity
        self._velocity_label.grid(row=2, column=0)
        self._velocity_entry.grid(row=2, column=1)

        # altitude
        self._altitude_label.grid(row=2, column=2)
        self._altitude_entry.grid(row=2, column=3)

        # tilt
        self._tilt_label.grid(row=3, column=0)
        self._tilt_entry.grid(row=3, column=1)

        # roll
        self._roll_label.grid(row=3, column=2)
        self._roll_entry.grid(row=3, column=3)

        # battery
        self._battery_label.grid(row=4, column=0)
        self._battery_entry.grid(row=4, column=1)

        # temperature
        self._temp_label.grid(row=4, column=2)
        self._temp_entry.grid(row=4, column=3)

    def update_variables(self, new_variables):
        # acceleration
        self.acceleration_x_var.set(new_variables[1])
        self.acceleration_y_var.set(new_variables[2])
        self.acceleration_z_var.set(new_variables[3])

        # velocity
        self.velocity_var.set(f"{new_variables[4]}")

        # altitude
        self.altitude_var.set(f"{new_variables[5]}")

        # tilt
        self.tilt_var.set(f"{new_variables[6]}")

        # roll
        self.roll_var.set(f"{new_variables[7]}")

        # battery
        self.battery_var.set(f"{new_variables[9]}")

        # temperature
        self.temp_var.set(f"{new_variables[10]}")
