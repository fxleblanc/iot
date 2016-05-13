import time

import RPi.GPIO as GPIO
import dht11

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()

instance = dht11.DHT11(pin=23)

while True:
    result = instance.read()
    if result.is_valid():
        print('Temperature: %d C' % result.temperature)
        print('Humidity: %d %%' % result.humidity)
    else:
        print("Error: %d" % result.error_code)

    time.sleep(1)
