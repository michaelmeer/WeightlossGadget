#!/usr/bin/python3

import logging
import logging.config
import time
from functools import partial
from tkinter import *
from tkinter.ttk import *
from multiprocessing import Process, Pipe
from PIL import Image, ImageTk

from weightloss_gadget.gui_actions import GuiActions


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
        leds_labelframe.pack(fill="both", expand="yes", side=TOP)
        self.led1 = Canvas(leds_labelframe, bg = "blue", height = 50, width = 50)
        self.led1.pack(side=LEFT)
        self.led2 = Canvas(leds_labelframe, bg = "green", height = 50, width = 50)
        self.led2.pack(side=LEFT)
        self.led3 = Canvas(leds_labelframe, bg = "red", height = 50, width = 50)
        self.led3.pack(side=LEFT)
        self.led4 = Canvas(leds_labelframe, bg = "yellow", height = 50, width = 50)
        self.led4.pack(side=LEFT)
        self.led5 = Canvas(leds_labelframe, bg = "yellow", height = 50, width = 50)
        self.led5.pack(side=LEFT)
        self.led6 = Canvas(leds_labelframe, bg = "yellow", height = 50, width = 50)
        self.led6.pack(side=LEFT)
        self.led7 = Canvas(leds_labelframe, bg = "yellow", height = 50, width = 50)
        self.led7.pack(side=LEFT)
        self.led8 = Canvas(leds_labelframe, bg = "yellow", height = 50, width = 50)
        self.led8.pack(side=LEFT)

        self.leds = [self.led1, self.led2, self.led3, self.led4, self.led5, self.led6, self.led7, self.led8]

        action_labelframe = LabelFrame(self.top, text = 'Actions')
        action_labelframe.pack(fill = "both", expand = "yes", side = BOTTOM)
        left_button = Button(action_labelframe, text = "<", command = partial(self.button_callback, GuiActions.LEFT))
        left_button.pack(side = LEFT, expand = True)
        center_button = Button(action_labelframe, text = "*", command = partial(self.button_callback, GuiActions.ACTION))
        center_button.pack(side = LEFT, expand = True)
        right_button = Button(action_labelframe, text = ">", command = partial(self.button_callback, GuiActions.RIGHT))
        right_button.pack(side = LEFT, expand = True)

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
            object  = self.pipe.recv()
            if isinstance(object, Image.Image):
                tk_image = ImageTk.PhotoImage(object)
                self.image_label.configure(image=tk_image)
                self.image_label.image = tk_image
                self.image_label.pack(side=TOP)
            elif isinstance(object, list):
                for led_widget, led_state in zip(self.leds, object):
                    led_widget.configure(bg=str(led_state))
            else:
                raise Exception("Received unknown object: %s (type: %s)"%(object, type(object)))
        self.top.after(100, self.check_pipe_poll)

class Ssd1306App(Process):
    def __init__(self, pipe):
        ### DISPLAY PART ###
        super().__init__()    
        self.logger = logging.getLogger("Ssd1306App")
        self.pipe = pipe
        # Raspberry Pi pin configuration:
        self.RST = 14
        # Note the following are only used with SPI:
        self.DC = 15
        self.SPI_PORT = 0
        self.SPI_DEVICE = 0
        # 128x64 display with hardware SPI:
        self.disp = Adafruit_SSD1306.SSD1306_128_64(rst=self.RST, dc=self.DC, spi=SPI.SpiDev(self.SPI_PORT, self.SPI_DEVICE, max_speed_hz=8000000))

        # Initialize library.
        self.disp.begin()
        # Clear display.
        self.disp.clear()
        self.disp.display()

        self.update_frequency = 0.1
        
        ### ROTARY ENCODER INPUT ###
        GPIO.setwarnings(True)
        GPIO.setmode(GPIO.BCM)        

        self.Enc_A = 5            
        self.Enc_B = 6             
        self.Button = 13
        
        # Assume that rotary switch is not moving while we init software
        self.Current_A = 1           
        self.Current_B = 1

        
        # define the Encoder switch inputs
        GPIO.setup(self.Enc_A, GPIO.IN, pull_up_down=GPIO.PUD_UP)             
        GPIO.setup(self.Enc_B, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # setup callback thread for the A and B encoder 
        # use interrupts for all inputs
        GPIO.add_event_detect(self.Enc_A, GPIO.RISING, callback=self.rotary_interrupt)
        GPIO.add_event_detect(self.Enc_B, GPIO.RISING, callback=self.rotary_interrupt)
        
        GPIO.setup(self.Button, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(self.Button, GPIO.FALLING, callback=self.button_interrupt)
    
    def button_interrupt(self, button):
        self.logger.debug("Button pressed")
        self.pipe.send(GuiActions.ACTION)
        
    def rotary_interrupt(self, A_or_B):
        Switch_A = GPIO.input(self.Enc_A)
        Switch_B = GPIO.input(self.Enc_B)

        if self.Current_A == Switch_A and self.Current_B == Switch_B:
            return

        self.Current_A = Switch_A                        # remember new state
        self.Current_B = Switch_B                        # for next bouncing check

        if (Switch_A and Switch_B):
          if A_or_B == self.Enc_B:                     # Turning direction depends on 
            self.logger.debug("Rotary Encoder turns right")
            self.pipe.send(GuiActions.RIGHT )
          else:
            self.logger.debug("Rotary Encoder turns left")
            self.pipe.send(GuiActions.LEFT )
        
    def run(self):
        self.logger.debug("check_pipe_poll")

        while True:
            if self.pipe.poll():
                pil_image = self.pipe.recv()
                self.disp.image(pil_image)
                self.disp.display()
            time.sleep(self.update_frequency)


