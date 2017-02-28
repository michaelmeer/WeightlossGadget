# !/usr/bin/python3
import configparser
import logging
import logging.config
from enum import Enum
from functools import partial
from multiprocessing import Pipe
from tkinter import *
from tkinter.ttk import *

from PIL import ImageTk

import screens


class GuiActions(Enum):
    LEFT_BUTTON = 1
    LEFT = 2
    ACTION = 3
    RIGHT = 4
    RIGHT_BUTTON = 5
    EXIT_PROGRAM = 6


class TkinterApp(object):
    def __init__(self, pipe):
        self.logger = logging.getLogger("TkinterApp")
        self.pipe = pipe

        self.top = Tk()
        self.top.title("Weightloss Tracker")
        screen_labelframe = LabelFrame(self.top, text = 'Screen')
        screen_labelframe.pack(fill = "both", expand = "yes", side = TOP)
        self.image_label = Label( screen_labelframe, relief = RAISED)
        self.image_label.pack(side = TOP)
        self.pipe = pipe

        leds_labelframe = LabelFrame(self.top, text = 'LEDs')
        leds_labelframe.pack(fill = "both", expand = "yes", side = TOP)
        led1 = Canvas(leds_labelframe, bg = "blue", height = 50, width = 50)
        led1.pack()
        action_labelframe = LabelFrame(self.top, text = 'Actions')
        action_labelframe.pack(fill = "both", expand = "yes", side = BOTTOM)
        b1_button = Button(action_labelframe, text = "B1", command = partial(self.button_callback, GuiActions.LEFT_BUTTON))
        b1_button.pack(side = LEFT, expand = True)
        left_button = Button(action_labelframe, text = "<", command = partial(self.button_callback, GuiActions.LEFT))
        left_button.pack(side = LEFT, expand = True)
        center_button = Button(action_labelframe, text = "*", command = partial(self.button_callback, GuiActions.ACTION))
        center_button.pack(side = LEFT, expand = True)
        right_button = Button(action_labelframe, text = ">", command = partial(self.button_callback, GuiActions.RIGHT))
        right_button.pack(side = LEFT, expand = True)
        b2_button = Button(action_labelframe, text = "B2", command = partial(self.button_callback, GuiActions.RIGHT_BUTTON))
        b2_button.pack(side = LEFT, expand = True)

        self.top.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.top.after(100, self.check_pipe_poll)

    def on_closing(self):
        self.pipe.send(GuiActions.EXIT_PROGRAM)
        self.top.destroy()


    def button_callback(self, action):
        self.pipe.send(action)


    def check_pipe_poll(self):
        self.logger.debug("check_pipe_poll")
        if self.pipe.poll():
            pil_image = self.pipe.recv()
            tk_image = ImageTk.PhotoImage(pil_image)
            self.image_label.configure(image=tk_image)
            self.image_label.image = tk_image

            self.image_label.pack(side=TOP)
        self.top.after(100, self.check_pipe_poll)


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read(r"config.ini")

    logging.config.fileConfig(config, disable_existing_loggers=False)
    screens.logging.config.fileConfig(config, disable_existing_loggers=False)
    logger = logging.getLogger(__name__)
    logger.info("Loaded Logging Configuration")

    parent_conn, child_conn = Pipe()
    controller_process = screens.Controller(child_conn)
    tkinter_app = TkinterApp(parent_conn)

    controller_process.start()
    tkinter_app.top.mainloop()
    controller_process.join()

