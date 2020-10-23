import pigpio
import time
import logging
import threading


class DCOutputDevice:
    """ Hardware interface class to handle the control of a DC output device which bi-directional output

        Attributes: direction     - GPIO pin number of the direction wire of the device
                    enable        - GPIO pin number of the enable wire of the device
                    stopFlag      - Flag to stop the current output operation
                    emergencyFlag - Flag to stop all DC output device operations for remaining of execution

        Methods:    stop()      - Flags stop to the current output operation on the specific DC output device
                    e_stop()    - Flags a stop to current and all future operation on all DC output devices
                                - Used for fatal errors to ensure outputs are turned off before exit
                    pulse(<direction of output(0 | 1)>, [<duration> = 1])
                                - Pulses the output in the input direction
                                - Optional duration parameter to set length of pulse in seconds
                    swap_pulse(<direction of first output(0 | 1)>, [<duration> = 1], [<combine_stop> = True])
                                - Pulses the output in the input direction followed by the revers direction
                                - Optional duration parameter to set length of pulse in seconds
                                - optional Boolean combine_stop parameter to set if a single stop call stops both pulses
                                > Default is True, single stop call stops both pulses
    """
    # GPIO object
    gpio = pigpio.pi()

    # Emergency stop flag for the DC Output devices
    # Thread safe equivalent to emergencyFlag = False
    emergencyFlag = threading.Event()

    # DC Output Device constructor
    # Inputs are Pi GPIO Pin numbers
    def __init__(self, in_direction, in_enable):
        """Creates an object to interface with hardware for a bi-directional DC output device

        :param in_direction: GPIO pin number of the direction wire of the device
        :param    in_enable: GPIO pin number of the enable wire of the device
        """
        self.direction = in_direction
        self.enable = in_enable

        # Initialise motor stop flag
        # Thread Safe Equivalent to self.stopFlag = False
        self.stopFlag = threading.Event()

        # Setup ENABLE pin as output
        DCOutputDevice.gpio.set_mode(self.enable, pigpio.OUTPUT)
        DCOutputDevice.gpio.write(self.enable, 0)
        logging.info(f"Setting up DC Output Device ENABLE on GPIO Pin: {self.enable}")

        # Setup DIRECTION pin as output
        DCOutputDevice.gpio.set_mode(self.direction, pigpio.OUTPUT)
        DCOutputDevice.gpio.write(self.direction, 0)
        logging.info(f"Setting up DC Output Device DIR on GPIO Pin: {self.direction}")

    def __del__(self):
        """Deconstruct to ensure outputs are disabled at exit

        :return: None
        """
        logging.info(f"Deconstructing DC Output Device ENABLE on GPIO Pin: {self.enable}")
        self.__disable_output()
        DCOutputDevice.gpio.stop()

    def __enable_output(self, in_dir):
        """Enables the DC Output in the input direction

        :param in_dir: Direction of output
        :return: None
        """
        # Check the emergency stop flag is not set
        if not DCOutputDevice.emergencyFlag.is_set():
            # Reset the stop flag for this operation
            self.stopFlag.clear()

            # Set the output pins to active as per input direction
            DCOutputDevice.gpio.write(self.direction, in_dir)
            DCOutputDevice.gpio.write(self.enable, 1)
        else:
            # Emergency Stop flag is set
            logging.error("DC Output not started due to Emergency Stop Flag set")

    def __disable_output(self):
        """Disables DC Output by drawing Enable pin low

        :return: None
        """
        # Set the output pins to low
        DCOutputDevice.gpio.write(self.enable, 0)
        DCOutputDevice.gpio.write(self.direction, 0)

    def stop(self):
        """Stops device output and sets the stopFlag flag to stop the current operation

        :return: None
        """
        # Stop Output
        self.__disable_output()
        # Set stop flag to notify to stop current output
        self.stopFlag.set()

        logging.info(f"DC Output Stop Flag Set to True {self.stopFlag.is_set()}")

    def e_stop(self):
        """Stops device output and sets the emergency stop flag to stop all dc device outputs

        :return: None
        """
        # Set emergency stop flag for the class to stop future operations
        DCOutputDevice.emergencyFlag.set()
        # Ensure current operation stops
        self.stop()

        logging.info(f"DC Output Emergency Stop Flag Set to {DCOutputDevice.emergencyFlag.is_set()}")

    def pulse(self, direction, duration=0):
        """Pulses the output in the input direction

        :param direction: Direction of pulse output (1 | 0)
        :param  duration: Optional duration parameter to set length of pulse in seconds
        :return:   count: Length of the pulse in seconds, -1 indicates the pulse was not completed
        """
        count = -1

        if duration == 0:
            # Perform an instant pulse
            logging.info(f"Pulsing Output DC Output in direction: {direction} on ENA Pin: {self.enable}")
            # Note no effect if emergency stop flag is set
            self.__enable_output(direction)
            self.__disable_output()
        else:
            # Perform a long pulse with length = duration
            logging.info(f"Activating Output for {duration} seconds, in direction: {direction} on ENA Pin: "
                         f"{self.enable}")
            count = self.__pulse_for(direction, duration)
        return count

    def swap_pulse(self, start_direction, duration=0, combine_stop=True):
        """Pulses the output in the input direction followed by the reverse direction

        :param start_direction: Direction of the first pulse output (1 | 0)
        :param        duration: Optional duration parameter to set length of pulse in seconds
        :param    combine_stop: Optional combine_stop parameter to set if a single stop call stops both pulses
                                Default is True, single stop call stops both pulses
        :return:        counts: length of each pulse in a list ordered [<first pulse>, <second_pulse>]
                                Values of -1 indicate pulses that were not completed
        """
        count = [-1, -1]

        if duration == 0:
            logging.info(f"Pulsing Output DC Output forwards than backwards starting with {start_direction} on ENA Pin:"
                         f" {self.enable}")
            # Pulse in first direction
            count[0] = self.pulse(start_direction)

            # Want to not perform reverse operation if the combine_stop flag is true and the stopFlag flag is set
            # This combines both pulses into a single operation stopped by a call to stop()
            if not (combine_stop and self.stopFlag.is_set()):
                # Pulse in the reverse direction
                count[1] = self.pulse((start_direction + 1) % 2)
        else:
            # Perform long swap pulse with length = duration
            logging.info(f"Activating Output DC Output forwards than backwards for {duration} seconds. Starting with"
                         f" {start_direction} on ENA Pin: {self.enable}")
            # Activate in first direction
            count[0] = self.__pulse_for(start_direction, duration)

            # Want to not perform reverse operation if the combine_stop flag is true and the stopFlag flag is set
            # This combines both pulses into a single operation stopped by a call to stop()
            if not (combine_stop and self.stopFlag.is_set()):
                # Activate in the reverse direction
                count[1] = self.__pulse_for((start_direction + 1) % 2, duration)

        # Return list of pulse lengths [<first pulse>, <second_pulse>]
        return count

    def __pulse_for(self, direction, duration):
        """Private function to pulse the output in the input direction for the input time

        :param direction: Direction of the first pulse output (1 | 0)
        :param  duration: Sets the length of pulse in seconds
        :return:   count: Actual length of the pulse in seconds, value of -1 indicates the pulse was not completed
        """
        if DCOutputDevice.emergencyFlag.is_set():
            logging.error("DC Output not started due to Emergency flag set")
            count = -1
        else:
            # Activate the output in the input direction
            self.__enable_output(direction)

            # Record the starting time of the output
            start = time.time()

            # Wait to be woken or for timer to expire
            # Return is True of stop flag is set, for False for timeout
            flag = self.stopFlag.wait(timeout=duration)

            # Disable the output
            self.__disable_output()

            # Save output length for reporting
            count = time.time() - start

            # Depending on result of waiting
            if flag:
                # The stop flag was set
                if DCOutputDevice.emergencyFlag.is_set():
                    logging.error("DC Output stopping due to Emergency flag set")
                elif self.stopFlag.is_set():
                    logging.info("DC Output stopping due to stop flag set")

                # Determine if no pulse was output
                if count < 0.001:
                    count = -1

            else:
                # The timeout duration was reached
                logging.info(f"DC Output duration reached on ENA pin: {self.enable}")

        return count
