# Developed By Keagan Bowman
# Blue Raven flight controller data simulator. Replicates data seen in a Blue Raven flight
# controller's output by loading it from a file.
#
# raven_simulator.py

import os
import time


class RavenSimulator:
    """
    This class establishes a fake Blue Raven data stream that simulates an actual device.

    Data is read from the specified sim_data file, and then passed out in the same clock cycle (0.22 seconds) that a
    blue raven uses. This allows for testing of the application and various features while the Blue Raven
    is not physically accessible.
    """

    def __init__(self, sim_data: str = "./simulation.dat"):

        if os.path.exists(sim_data):
            self.data_stream = open(sim_data, "wb")
        else:
            print("Unable to create datastream, path invalid.")

    def get_next_line(self):
        while True:
            # get next line from data stream
            data = self.data_stream.readline()

            # ensure that this is flight data - we can ignore all others for now
            if b"BLR_STAT" in data:
                break

        # simulated data gather delay
        time.sleep(0.22)

        # return data
        return data

