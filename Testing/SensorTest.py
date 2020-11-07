from component_control.hardware_interface.PhotoSensor import PhotoSensor
import logging
import time

# Rate of Sensor reading and output in samples/second
SAMPLE_RATE = 100

# GPIO pin of the head home sensor
TRAVPS = 4
# GPIO Input for the sensor to return True
TRAVPS_TRUE = 1

# GPIO pin of the tool selector home sensor
TOOLPS = 17
# GPIO Input for the sensor to return True
TOOLPS_TRUE = 0

# GPIO pin of the tool selector home sensor
EMBPS = 7
# GPIO Input for the sensor to return True
EMBPS_TRUE = 1

# Dictionary of sensor info, any sensors added here will be sampled and output
SENSOR_INFO = {'Traverse Home': (TRAVPS,TRAVPS_TRUE), 
               'Tool Home': (TOOLPS,TOOLPS_TRUE), 
               'Embosser Home': (EMBPS,EMBPS_TRUE)}

def main():
    logging.basicConfig(level=logging.INFO)

    sensors = {}
    
    for name, sense in SENSORS.items():
	    sensors[name] = PhotoSensor(sense[0], sense[1])
        
    while True:
        print("")
        
        for name, sensor in sensors.items():
		    print(f"{name} Sensor Output: {sensor.read_sensor()}")
        
        time.sleep(1 / SAMPLE_RATE)


if __name__ == '__main__':
        main()
