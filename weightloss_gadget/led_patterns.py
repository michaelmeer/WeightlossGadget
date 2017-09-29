import time
from math import floor

class pixel(object):
    def __init__(self, r, g, b):
        self.r = r
        self.g = g
        self.b = b

    def __str__(self):
        color_string = "#%.2X%.2X%.2X" % (self.r, self.g, self.b)
        return color_string


class red_blinking_pattern(object):
    def __init__(self):
        self.counter = 0

        self.start_time = time.clock()
        self.next_update_time = floor(self.start_time)
        self.is_running = True

    def does_need_update(self):
        if self.is_running and self.next_update_time < time.clock():
            self.next_update_time += 2.0
            return True
        else:
            return False

    def stop(self):
        self.is_running = False

    def create_led_pattern(self):
        self.counter += 1
        if self.counter % 2:
            return [pixel(0,255,0) for x in range(8)]
        else:
            return [pixel(0, 0, 0) for x in range(8)]

    def end_led_pattern(self):
        return [pixel(0, 0, 0) for x in range(8)]