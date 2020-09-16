# Class: StepperMotor
# Desc: Hardware interface class to handle the control of a stepper motor
# Params: in_direction is the gpio pin number of the direction wire of the motor
#         in_step is the gpio pin number of the step wire of the motor
#         in_enable is the gpio pin number of the enable wire of the motor
#         in_start_speed is the starting speed of the motor
#         in_max_speed is the maximum speed of the motor
#
# Functions: move_steps(<number of steps>, <direction of movement(0 | 1)> )
#               - rotates the motor the input number of steps

import pigpio
import time


class StepperMotor:
    gpio = pigpio.pi()
    ramp_rate = 0.1

    def __init__(self, in_direction=None, in_step=None, in_enable=None, in_start_speed=None, in_max_speed=None):
        self.direction = in_direction
        self.step = in_step
        self.enable = in_enable

        self.startSpeed = in_start_speed
        self.maxSpeed = in_max_speed

        StepperMotor.gpio.write(self.enable, 0)
        StepperMotor.gpio.write(self.step, 0)
        StepperMotor.gpio.write(self.direction, 0)

    def move_steps(self, count, in_direction):
        # Set enable pin high
        StepperMotor.gpio.write(self.enable, 1)
        # Set direction pin
        StepperMotor.gpio.write(self.direction, in_direction)

        speed = self.startSpeed

        ramp_length = (speed - self.maxSpeed) / StepperMotor.ramp_rate

        for i in range(0, count):

            __step_motor(speed)

            # Ramp up speed at start of movement
            if i < ramp_length:
                speed += StepperMotor.ramp_rate

            # Ramp down speed at end of movement
            if i > (count - ramp_length):
                speed -= StepperMotor.ramp_rate

        # Set enable pin low
        StepperMotor.gpio.write(self.enable, 0)

    # Function to move motor until the function in the in_condition parameter returns TRUE
    def move_until(self, in_direction, in_condition):
        # Set enable pin high
        StepperMotor.gpio.write(self.enable, 1)
        # Set direction pin
        StepperMotor.gpio.write(self.direction, in_direction)

        while not in_condition():
            self.__step_motor(self.startSpeed)

        # Set enable pin low
        StepperMotor.gpio.write(self.enable, 0)

    def __step_motor(self, speed):
        # Pulse Step Pin
        StepperMotor.gpio.write(self.step, 1)
        #
        StepperMotor.gpio.write(self.step, 0)

        # Wait - Sets speed
        # Transforms speed to a delay between steps
        time.sleep(1 / (1 + (speed * 100)))
