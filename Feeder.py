# Class: DCOutputDevice
# Desc: Hardware interface class to handle the control of a stepper motor
# Params: in_direction is the gpio pin number of the direction wire of the motor
#         in_step is the gpio pin number of the step wire of the motor
#         in_enable is the gpio pin number of the enable wire of the motor
#         in_start_speed is the starting speed of the motor
#         in_max_speed is the maximum speed of the motor
#
# Functions: move_steps(<number of steps>, <direction of movement(0 | 1)> )
#               - rotates the motor the input number of steps
#            move_until(<condition function>, <direction of movement (0 | 1)> )
#               - rotates the motor in the input direction until the condition function returns true
import pigpio
import time
import logging
from StepperMotor import StepperMotor
from DCOutputDevice import DCOutputDevice
from PhotoSensor import PhotoSensor


class Feeder:

    # // Line Feed Stepper Motor //
    # GPIO pins of the line feed stepper motor
    LNFDIR = 24
    LNFSTEP = 18
    LNFENA = 23
    # Motor speed parameters to be tuned during testing
    START_SPEED = 5
    MAX_SPEED = 10
    # Motor directional parameters
    LNF_POS_DIR = 1
    LNF_NEG_DIR = 0

    # // Paper Feed DC Motor //
    # GPIO pins of the paper feed DC motor
    PPRDIR = 25
    PPRENA = 12
    # Motor Directional parameters
    PPR_POS_DIR = 1
    PPR_NEG_DIR = 0

    # // Input Side Paper Sensor //
    # GPIO pin of the input side paper sensor
    PBOTPS = 22
    # GPIO Input for the sensor to return True
    PBOTPS_TRUE = 0

    # // Output Side Paper Sensor //
    # GPIO pin of the output side paper sensor
    PTOPPS = 17
    # GPIO Input for the sensor to return True
    PBTOPPS_TRUE = 0

    # // A4 Paper Size Sensor //
    # GPIO pin of the A4 size paper sensor
    A4PPRPS = 14
    # GPIO Input for the sensor to return True
    A4PPRPS_TRUE = 0

    # // Braille Paper Size Sensor //
    # GPIO pin of the A4 size paper sensor
    BPPRPS = 15
    # GPIO Input for the sensor to return True
    BPPRPS_TRUE = 0

    def __init__(self):
        # Construct Line Stepper
        self.LineStepper = StepperMotor(Feeder.LNFDIR, Feeder.LNFSTEP, Feeder.LNFENA,
                                         Feeder.START_SPEED, Feeder.MAX_SPEED)
        logging.info(f"Setting up Line Feed Stepper with STEP Pin: {Feeder.LNFSTEP}")

        # Construct Paper Feed
        self.PaperFeed = DCOutputDevice(Feeder.PPRDIR, Feeder.PPRENA)
        logging.info(f"Setting up Paper Feed Motor with ENA Pin: {Feeder.PPRENA}")

        self.LineInputSensor = PhotoSensor(Feeder.PBOTPS, Feeder.PBOTPS_TRUE)
        logging.info(f"Setting up Paper Input Sensor on Pin: {Feeder.PBOTPS}")

        self.LineInputSensor = PhotoSensor(Feeder.PTOPPS, Feeder.PBTOPPS_TRUE)
        logging.info(f"Setting up Paper Output Sensor on Pin: {Feeder.PTOPPS}")

        self.LineInputSensor = PhotoSensor(Feeder.A4PPRPS, Feeder.A4PPRPS_TRUE)
        logging.info(f"Setting up A4 Paper Size Sensor on Pin: {Feeder.A4PPRPS}")

        self.LineInputSensor = PhotoSensor(Feeder.BPPRPS, Feeder.BPPRPS_TRUE)
        logging.info(f"Setting up Braille Paper Size Sensor on Pin: {Feeder.BPPRPS}")

    # Returns the size of the paper in number of characters
    # Note that
    def get_paper_size(self):


    def feed_line(self):


    def feed_lines(self, count):
        for i in range(count):
            self.feed_line()


