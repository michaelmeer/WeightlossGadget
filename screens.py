import sys
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageTk
from multiprocessing import Process
import time
import socket
import logging
import configparser
from gui_actions import GuiActions
from enum import Enum

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64
"""
Fill 0 -> black, 1 -> white
"""

fnt = ImageFont.truetype(r'resources\Roboto-Bold.ttf', 14)

class Color(Enum):
    BLACK = 0
    WHITE = 1

class Controller(Process):
    def __init__(self, pipe):
        super().__init__()
        self.config = configparser.ConfigParser()
        self.config.read(r"config.ini")
        logging.config.fileConfig(self.config, disable_existing_loggers=False)

        self.get_logger()
        self.pipe = pipe
        self.screens = [WatchScreen(), WeightInputScreen(), IpAddressScreen()]
        self.update_frequency = 0.1

        self.logger.info("Controller initialized")

    def get_logger(self):
        logging.config.fileConfig(self.config, disable_existing_loggers=False)
        self.logger = logging.getLogger(self.__class__.__name__)

    def __getstate__(self):
        self_dict = self.__dict__
        del self_dict['logger']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.get_logger()

    def run(self):
        process_running = True
        while process_running:
            if self.get_current_screen().does_need_update():
                picture = self.get_current_screen().create_image()
                self.pipe.send(picture)

            if self.pipe.poll():
                received_object = self.pipe.recv()
                self.logger.info ("Controller: Received object: %s (type %s)"%(received_object, type(received_object)))
                if received_object.value == GuiActions.EXIT_PROGRAM.value:
                    self.logger.debug("Controller: shutting down")
                    process_running = False
                if self.get_current_screen().handles_input() and self.get_current_screen().input_mode:
                    self.get_current_screen().handle_input(received_object)
                else:
                    if received_object.value == GuiActions.LEFT.value:
                        self.switch_current_screen(-1)
                    elif received_object.value == GuiActions.RIGHT.value:
                        self.switch_current_screen(1)
                    elif received_object.value == GuiActions.ACTION.value:
                        if self.get_current_screen().handles_input():
                            self.get_current_screen().set_input_mode(not self.get_current_screen().input_mode)
            time.sleep(self.update_frequency)

    def get_current_screen(self):
        if not hasattr(self, "current_screen_index"):
            self.current_screen_index = 1

        return self.screens[self.current_screen_index]

    def switch_current_screen(self, delta):
        min_allowed_index = 0
        max_allowed_index = len(self.screens)-1

        self.current_screen_index += delta

        if self.current_screen_index < min_allowed_index:
            self.current_screen_index = max_allowed_index

        if self.current_screen_index > max_allowed_index:
            self.current_screen_index = min_allowed_index

        picture = self.get_current_screen().create_image()
        self.pipe.send(picture)

class AbstractScreen(object):
    def __init__(self):
        self.get_logger()

    def get_logger(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def __getstate__(self):
        self_dict = self.__dict__
        del self_dict['logger']
        return self_dict

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.get_logger()

    def handles_input(self):
        return False

class WatchScreen(AbstractScreen):
    def __init__(self):
        super().__init__()
        self.update_frequency = 0.5
        self.counter = 0

    def does_need_update(self):
        self.counter += 1
        return self.counter % 5 == 0

    def create_image(self):
        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 128)
        draw = ImageDraw.Draw(im)

        now = datetime.now()
        time_text = now.time().isoformat()
        date_text = now.date().strftime('%Y-%m-%d')
        self.logger.debug("time used in picture: %s" % time_text)
        draw.text((0, 0), time_text, font=fnt)
        draw.text((0, 30), date_text, font=fnt)

        del draw
        return im

class IpAddressScreen(AbstractScreen):
    def __init__(self):
        super().__init__()
        self.update_frequency = 0.5
        self.counter = 0

    def does_need_update(self):
        self.counter += 1
        return self.counter <= 1

    def create_image(self):
        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color = 0)
        draw = ImageDraw.Draw(im)
        ip_address = socket.gethostbyname(socket.gethostname())

        draw.text((0, 0), ip_address, font=fnt, fill=1)
        del draw
        return im

class WeightInputScreen(AbstractScreen):
    def __init__(self, name = "Michael", current_weight = 100.0):
        super().__init__()
        self.name = name
        self.current_weight = current_weight
        self.update_frequency = 0.5
        self.counter = 0
        self.input_mode = False

    def does_need_update(self):
        self.counter += 1
        return self.counter % 2 == 0

    def create_image(self):
        if self.input_mode:
            FG = 1
            BG = 0
        else:
            FG = 0
            BG = 1

        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color=BG)
        draw = ImageDraw.Draw(im)

        draw.text((0, 0), self.name, font=fnt, fill=FG)
        weight_str ="%5.1f"%self.current_weight
        self.logger.debug("Counter: %i", self.counter)
        if self.input_mode and self.counter%3 == 0:
            weight_str = weight_str[:-1]+' '

        draw.text((30, 20), weight_str, font=fnt, fill=FG)
        del draw
        return im

    def handles_input(self):
        return True

    def set_input_mode(self, mode):
        self.input_mode = mode

    def input_mode(self, mode):
        return self.input_mode

    def handle_input(self, input):
        if input.value == GuiActions.ACTION.value:
            self.set_input_mode(False)
        elif input.value == GuiActions.LEFT.value:
            self.current_weight += -0.1
        elif input.value == GuiActions.RIGHT.value:
            self.current_weight += 0.1
