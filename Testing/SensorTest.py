from component_control.hardware_interface.PhotoSensor import PhotoSensor
import logging
import time

# GPIO pin of the head home sensor
TRAVPS = 4
# GPIO Input for the sensor to return True
TRAVPS_TRUE = 1

# GPIO pin of the tool selector home sensor
TOOLPS = 27
# GPIO Input for the sensor to return True
TOOLPS_TRUE = 0

# GPIO pin of the tool selector home sensor
EMBPS = 7
# GPIO Input for the sensor to return True
EMBPS_TRUE = 1


def main():
    logging.basicConfig(level=logging.INFO)

    trav = PhotoSensor(TRAVPS, TRAVPS_TRUE)
    tool = PhotoSensor(TOOLPS, TOOLPS_TRUE)
    emb = PhotoSensor(EMBPS, EMBPS_TRUE)

    while True:
            print(f"Traverse Home Sensor Output: {trav.read_sensor()}")
            print(f"Tool Blank Sensor Output: {tool.read_sensor()}")
            print(f"Embosser Home Sensor Output: {emb.read_sensor()}")

            print("\n")

            time.sleep(0.01)


if __name__ == '__main__':
        main()