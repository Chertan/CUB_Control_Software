import pigpio
import time
import logging
import threading


class StepperMotor:
    """Hardware interface class to handle the control of a stepper motor connected via a stepper motor driver

        Attributes: direction      - GPIO pin number of the direction wire of the motor
                    step           - GPIO pin number of the step wire of the motor
                    enable         - GPIO pin number of the enable wire of the motor
                    start_speed    - Starting speed of the motor (steps/second)
                    max_speed      - Maximum speed of the motor (steps/second)
                    ramp_rate      - Ramp rate of motor (steps increased per step)
                    stopFlag    - Flag to stop the current output operation
                    emergencyFlag - Flag to stop all DC output device operations for remaining of execution

        Methods:    stop()      - Sets the stop flag for the stepper motor, stopping the current operation
                    e_stop()    - Sets the Emergency stop flag for the class, stopping all Stepper motor operations
                    move_steps(<number of steps>, <direction of movement(0 | 1)> )
                                - rotates the motor the input number of steps or until stop is called
    """
    # GPIO object
    gpio = pigpio.pi()

    # Emergency stop flag for the stepper motors
    # Setting the flag will stop all motors from rotating
    # Thread safe equivalent to emergencyFlag = False
    emergencyFlag = threading.Event()

    # Speed where the output is delayed by only the software and gpio overhead
    CLIP_SPEED = 2000

    def __init__(self, in_direction, in_step, in_enable, in_start_speed, in_max_speed, in_ramp_rate):
        """
        Creates an object to interface with a Stepper motor connected via a stepper controller
        :param   in_direction: GPIO pin number of the direction wire of the motor
        :param        in_step: GPIO pin number of the step wire of the motor
        :param      in_enable: GPIO pin number of the enable wire of the motor
        :param in_start_speed: Starting speed of the motor (steps/second)
        :param   in_max_speed: Maximum speed of the motor (steps/second)
        :param   in_ramp_rate: Ramp rate of motor (steps increased per step)
        """
        # Save Motor GPIO pins
        self.direction = in_direction
        self.step = in_step
        self.enable = in_enable

        # Speed is in steps per second
        # Used to determine motor ramp and operation speeds
        self.startSpeed = in_start_speed
        self.maxSpeed = in_max_speed
        self.rampRate = in_ramp_rate

        # Initialise motor stop flag
        # Thread Safe Equivalent to self.stopFlag = False
        self.stopFlag = threading.Event()

        # Setup ENABLE Pin as output
        StepperMotor.gpio.set_mode(self.enable, pigpio.OUTPUT)
        StepperMotor.gpio.write(self.enable, 0)
        logging.info(f"Setting up Stepper ENABLE on GPIO Pin: {self.enable}")

        # Setup STOP pin as output
        StepperMotor.gpio.set_mode(self.step, pigpio.OUTPUT)
        StepperMotor.gpio.write(self.step, 0)
        logging.info(f"Setting up Stepper STEP on GPIO Pin: {self.step}")

        # Setup DIRECTION pin as output
        StepperMotor.gpio.set_mode(self.direction, pigpio.OUTPUT)
        StepperMotor.gpio.write(self.direction, 0)
        logging.info(f"Setting up Stepper DIR on GPIO Pin: {self.direction}")

    def __startup_motor(self, in_dir):
        """
        Initialises motor ready for a movement in the input direction
        :param in_dir: Direction of motor rotation for next operation
        :return: None
        """
        # Check if the emergency stop Event flag is set
        if not StepperMotor.emergencyFlag.is_set():
            self.stopFlag.clear()
            StepperMotor.gpio.write(self.direction, in_dir)
            StepperMotor.gpio.write(self.enable, 1)

        else:
            logging.error("Stepper not started due to Emergency Stop Flag set")

    def __disable_motor(self):
        """
        Disables outputs of the motor by setting all output pins low
        Note this stops stepper motors from holding their position
        May cause inaccuracies in steps if disabled between movements
        :return: None
        """
        StepperMotor.gpio.write(self.enable, 0)
        StepperMotor.gpio.write(self.step, 0)
        StepperMotor.gpio.write(self.direction, 0)

    def __step_motor(self, speed):
        """
        Steps the motor at a maximum speed of the input speed (in steps per second)
        :param speed: Desired speed of the motor in steps per second
        :return: None
        """
        # Transforms speed to a time between steps (n steps per second = 1/n seconds between steps)
        if speed > 0:
            logging.debug(f"Stepping Motor with speed: {speed}")
            # sleep to limit the steps per second to match the input speed
            time.sleep(1 / speed)

            # Pulse Step Pin
            StepperMotor.gpio.write(self.step, 1)
            StepperMotor.gpio.write(self.step, 0)
        else:
            self.stop()

    def stop(self):
        """
        Stops the current operation of the motor
        Does not disable motor in order to maintain holding torque
        :return: None
        """
        self.stopFlag.set()
        logging.debug("Stepper Motor Stop Flag Set to True")

    def e_stop(self):
        """
        Flags a permanent stop to the stepper motors
        Also disables the motor for safety as no further operations can be completed
        :return:
        """
        StepperMotor.emergencyFlag.set()
        self.__disable_motor()
        logging.info("Stepper Motor Emergency Stop Flag Set to True")

    def move_steps(self, count, in_direction):
        """
        Move steps equal to the input count in the input direction
        :param        count: Number of steps to move
        :param in_direction: Direction of motor rotation
        :return: step_count: Actual number of step taken for operation
        """
        # Set enable pin high
        # Set direction pin
        self.__startup_motor(in_direction)

        logging.info(f"Stepping Stepper by {count} steps, in direction: {in_direction} on STEP Pin: {self.step}")

        speed = self.startSpeed

        ramp_length = (self.maxSpeed - speed) / self.rampRate

        step_count = count

        for i in range(0, count):

            if StepperMotor.emergencyFlag.is_set():
                logging.info("Stepper Motor stopping due to Emergency flag set")
                step_count = i
                break

            if self.stopFlag.is_set():
                logging.info("Stepper Motor stopping due to stop flag set")
                step_count = i
                break

            self.__step_motor(speed)

            # Ramp up speed at start of movement
            if i < ramp_length:
                speed += self.rampRate

            # Ramp down speed at end of movement
            # count -1 for index from 0, total -1 as it is decremented after step
            if i > (((count-1) - ramp_length) -1):
                speed -= self.rampRate

        # Set all output pins low
        # self.__disable_motor()

        return step_count
