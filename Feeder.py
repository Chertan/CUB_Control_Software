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

class Feeder:

