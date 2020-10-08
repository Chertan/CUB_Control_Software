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
import threading


class DCOutputDevice:
    gpio = pigpio.pi()

    # Emergency stop flag for the DC Output devices
    # Setting to True will stop all DC Output devices from activating
    emergency_stop = False

    # DC Output Device constructor
    # Inputs are Pi GPIO Pin numbers
    def __init__(self, in_direction=None, in_enable=None):
        self.direction = in_direction
        self.enable = in_enable

        self.stop_output = False
        self.sleep_condition = threading.Condition()

        DCOutputDevice.gpio.set_mode(self.enable, pigpio.OUTPUT)
        DCOutputDevice.gpio.write(self.enable, 0)
        logging.info(f"Setting up DC Output Device ENABLE on GPIO Pin: {self.enable}")

        DCOutputDevice.gpio.set_mode(self.direction, pigpio.OUTPUT)
        DCOutputDevice.gpio.write(self.direction, 0)
        logging.info(f"Setting up DC Output Device DIR on GPIO Pin: {self.direction}")

    # Used to enable the DC output
    # Does not enable if the emergency stop flag is set
    def __enable_output(self, in_dir):
        if not DCOutputDevice.emergency_stop:
            self.stop_output = False
            DCOutputDevice.gpio.write(self.direction, in_dir)
            DCOutputDevice.gpio.write(self.enable, 1)

        else:
            logging.error("DC Output not started due to Emergency Stop Flag set")

    # Used to disable the DC Output
    def __disable_output(self):
        DCOutputDevice.gpio.write(self.enable, 0)
        DCOutputDevice.gpio.write(self.direction, 0)

    # Stops the current operation
    def stop(self):
        self.stop_output = True
        self.__disable_output()

        logging.error("DC Output Stop Flag Set to True")
        self.sleep_condition.notify()

    # Sets the emergency flag
    def e_stop(self):
        DCOutputDevice.emergency_stop = True
        self.__disable_output()
        self.sleep_condition.notify()

        logging.error("DC Output Emergency Stop Flag Set to True")
        self.sleep_condition.notify()

    # Pulses the output in the input direction
    def pulse(self, in_direction):
        logging.error("Pulsing Output DC Output in direction: {in_direction} on ENA Pin: {self.enable}")

        self.__enable_output(in_direction)
        self.__disable_output()

    def swap_pulse(self, start_direction):
        logging.error("Pulsing Output DC Output forwards than backwards starting with {start_direction} on ENA Pin: "
                      "[self.enable}")

        self.__enable_output(start_direction)

        if start_direction == 1:
            self.__enable_output(0)
        else:
            self.__enable_output(1)

        self.__disable_output()

    # Activates the output until the function in the in_condition parameter returns TRUE
    # Returns the length of time in seconds that the output was active for
    def on_until(self, in_condition, in_direction):

        logging.info(f"Activating Output until {in_condition.__name__}, in direction: {in_direction} on ENA Pin: "
                     f"{self.enable}")

        # Activate the output in the input direction
        self.__enable_output(in_direction)

        # Record the starting time of the output
        start = time.time()

        while not in_condition():
            if DCOutputDevice.emergency_stop:
                logging.info("DC Output stopping due to Emergency flag set")
                break

            if self.stop_output:
                logging.info("Stepper Motor stopping due to stop flag set")
                break

        # Disable the output
        self.__disable_output()

        # Return the total time in seconds that the output was active
        count = time.time() - start
        return count

    # Activates the input for a length of time
    def on_for(self, in_time, in_direction):

        logging.info(f"Activating Output for {in_time} seconds, in direction: {in_direction} on ENA Pin: "
                     f"{self.enable}")

        # Activate the output in the input direction
        self.__enable_output(in_direction)

        # Record the starting time of the output
        start = time.time()

        # Wait to be woken or for timer to expire
        result = self.sleep_condition.wait(timeout=in_time)

        if not result:
            if DCOutputDevice.emergency_stop:
                logging.info("DC Output stopping due to Emergency flag set")

            if self.stop_output:
                logging.info("DC Output stopping due to stop flag set")

            count = time.time() - start
        else:
            count = in_time

            # Disable the output
            self.__disable_output()

        return count
