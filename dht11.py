"""
The following code is adapted from https://github.com/szazo/DHT11_Python .
Theses modifications are under the GPLv3.
"""

import time
import RPi.GPIO as GPIO


class DHT11Result:
    'DHT11 sensor result returned by DHT11.read() method'

    ERR_NO_ERROR = 0
    ERR_MISSING_DATA = 1
    ERR_CRC = 2

    def __init__(self, temperature=None, humidity=None, error=ERR_NO_ERROR):
        self.temperature = temperature
        self.humidity = humidity
        self.error = error

    def is_valid(self):
        return self.error == DHT11Result.ERR_NO_ERROR


class DHT11:
    'DHT11 sensor reader class for Rpi.GPIO library (works with Pine64 port)'

    __pin = 0

    def __init__(self, pin):
        self.__pin = pin

    def read(self):
        GPIO.setup(self.__pin, GPIO.OUT)

        # send initial high to DHT11
        self.__send_and_sleep(GPIO.HIGH, 0.05)

        # pull down to low
        GPIO.output(self.__pin, GPIO.LOW)
        time.sleep(0.02)

        # listen to DHT11
        GPIO.setup(self.__pin, GPIO.IN, GPIO.PUD_UP)

        # collect data into an array
        data = self.__collect_input()
        from itertools import groupby

        print('len %d' % len([x[0] for x in groupby(data)]))
        print(['%d %s' % (x[0], vars(x[1])) for x in groupby(data)])

        # parse lengths of all data pull up periods
        pull_up_lengths = self.__parse_data_pull_up_lengths(data)
        print('pull up len %d ' % len(pull_up_lengths))

        # if bit count mismatch, return error (4 byte data + 1 byte checksum)
        if len(pull_up_lengths) != 40:
            return DHT11Result(error=DHT11Result.ERR_MISSING_DATA)

        # calculate bits from lengths of the pull up periods
        bits = self.__calculate_bits(pull_up_lengths)

        # we have the bits, calculate bytes
        the_bytes = self.__bits_to_bytes(bits)

        # calculate checksum and check
        checksum = self.__calculate_checksum(the_bytes)
        if the_bytes[4] != checksum:
            return DHT11Result(error=DHT11Result.ERR_CRC)

        # ok, we have valid data, return it
        return DHT11Result(the_bytes[2], the_bytes[0])

    def __send_and_sleep(self, output, sleep):
        GPIO.output(self.__pin, output)
        time.sleep(sleep)

    def __collect_input(self):
        # collect the data while unchanged found
        unchanged_count = 0

        # this is used to determine where is the end of the data
        max_unchanged_count = 64

        last = -1
        data = []
        while unchanged_count < max_unchanged_count:
            current = GPIO.input(self.__pin)
            data.append(current)

            if last != current:
                unchanged_count = 0
                last = current
            elif current == 1:
                unchanged_count += 1

        print(len(data))
        return data

    def __parse_data_pull_up_lengths(self, data):
        STATE_INIT_PULL_DOWN = 1
        STATE_INIT_PULL_UP = 2
        STATE_DATA_FIRST_PULL_DOWN = 3
        STATE_DATA_PULL_UP = 4
        STATE_DATA_PULL_DOWN = 5

        state = STATE_INIT_PULL_DOWN

        lengths = []  # will contain the lengths of data pull up periods
        current_length = 0  # will contain the length of the previous period

        for current in data:
            current_length += 1

            if current == GPIO.LOW:
                if state == STATE_INIT_PULL_DOWN:
                    # ok, we got the initial pull down
                    state = STATE_INIT_PULL_UP
                elif state == STATE_DATA_FIRST_PULL_DOWN:
                    # we have the initial pull down
                    # the next will be the data pull up
                    state = STATE_DATA_PULL_UP
                elif state == STATE_DATA_PULL_DOWN:
                    # we store the length of the previous pull up period
                    lengths.append(current_length)
                    state = STATE_DATA_PULL_UP
            elif current == GPIO.HIGH:
                if state == STATE_INIT_PULL_UP:
                    # ok, we got the initial pull up
                    state = STATE_DATA_FIRST_PULL_DOWN
                elif state == STATE_DATA_PULL_UP:
                    # the length of this pull up will determine
                    # whether it is 0 or 1
                    current_length = 0
                    state = STATE_DATA_PULL_DOWN
            else:
                print('invalid state at %d' % current_length)
        return lengths

    def __calculate_bits(self, pull_up_lengths):

        # find shortest and longest period
        shortest_pull_up = 1000
        longest_pull_up = 0

        for i in range(0, len(pull_up_lengths)):

            length = pull_up_lengths[i]
            if length < shortest_pull_up:
                shortest_pull_up = length

            if length > longest_pull_up:
                longest_pull_up = length

        # use the halfway to determine whether the period it is long or short
        halfway = shortest_pull_up + (longest_pull_up - shortest_pull_up) / 2

        bits = []

        for i in range(0, len(pull_up_lengths)):

            bit = False
            if pull_up_lengths[i] > halfway:
                bit = True

            bits.append(bit)

        return bits

    def __bits_to_bytes(self, bits):

        the_bytes = []
        byte = 0

        for i in range(0, len(bits)):

            byte = byte << 1
            if (bits[i]):
                byte = byte | 1
            else:
                byte = byte | 0

            if ((i + 1) % 8 == 0):
                the_bytes.append(byte)
                byte = 0

        return the_bytes

    def __calculate_checksum(self, the_bytes):
        return the_bytes[0] + the_bytes[1] + the_bytes[2] + the_bytes[3] & 255
