from multiprocessing import Process, Pipe
import configparser
import logging
import re
import time
from weightloss_gadget import user_interface, screens, gui_actions

GuiActions = gui_actions.GuiActions

class Controller(Process):
    def __init__(self, pipe, config):
        super().__init__()
        self.config = config
        logging.config.fileConfig(self.config, disable_existing_loggers=False)

        self.get_logger()
        self.pipe = pipe

        self.screens = self.setup_screens_from_config()
        self.update_frequency = 0.1

        self.logger.info("Controller initialized")

    def available_screen_classes(self):
        screen_classes = screens.AbstractScreen.__subclasses__()
        screen_classes_dictionary = {screen_class.__name__:screen_class for screen_class in screen_classes}
        return screen_classes_dictionary

    def setup_screens_from_config(self):
        available_screen_classes = self.available_screen_classes()
        screen_instances = []
        section_name_cleaner = "(?P<cleaned_section_name>[A-Za-z_]+)[0-9]*"
        for section_name in self.config.sections():
            result = re.match(section_name_cleaner, section_name)
            possible_screen_class_name = result.group("cleaned_section_name")
            if possible_screen_class_name and possible_screen_class_name in available_screen_classes:
                self.logger.info("Initiating screen instance of type %s", section_name)
                screen_class = available_screen_classes[possible_screen_class_name]
                screen_instance = screen_class(self.config[section_name])
                screen_instances.append(screen_instance)

        return screen_instances

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
                self.send_picture_to_controller(picture)

                led_pattern = self.get_current_screen().create_led_pattern()
                self.pipe.send(led_pattern)

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

    def send_picture_to_controller(self, picture):
        if self.config.getboolean('weightloss_gadget', 'rotate_screen', fallback=False):
            picture = picture.rotate(180)
        self.pipe.send(picture)

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
        self.send_picture_to_controller(picture)

def main():
    config = configparser.ConfigParser()
    config.read(r"../config.ini") # @TODO: find the correct file once this is all packaged nicely

    logging.config.fileConfig(config, disable_existing_loggers=False)
    #screens.logging.config.fileConfig(config, disable_existing_loggers=False)
    logger = logging.getLogger(__name__)
    logger.info("Loaded Logging Configuration")

    parent_conn, child_conn = Pipe()

    controller_process = Controller(child_conn, config)

    frontend = config['weightloss_gadget']['frontend']
    if frontend == 'TkInter':
        tkinter_app = user_interface.TkinterApp(parent_conn)
        controller_process.start()
        tkinter_app.top.mainloop()
        controller_process.join()
    elif frontend == 'Ssd1306':
        import Adafruit_GPIO.SPI as SPI
        import Adafruit_SSD1306
        import RPi.GPIO as GPIO

        ssd1306_app = user_interface.Ssd1306App(parent_conn)
        ssd1306_app.start()
        controller_process.start()
        controller_process.join()
        ssd1306_app.join()

if __name__ == '__main__':
    main()