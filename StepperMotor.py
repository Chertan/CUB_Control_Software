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

            # Pulse Step Pin
            StepperMotor.gpio.write(self.step, 1)
            StepperMotor.gpio.write(self.step, 0)

            # Ramp up speed at start of movement
            if i < ramp_length:
                speed += StepperMotor.ramp_rate

            # Ramp down speed at end of movement
            if i > (count - ramp_length):
                speed -= StepperMotor.ramp_rate

            # Wait - Sets speed
            # Transforms speed to a delay between steps
            time.sleep(1 / (1 + (speed * 100)))

        # Set enable pin low
        StepperMotor.gpio.write(self.enable, 0)
