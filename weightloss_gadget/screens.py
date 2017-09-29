import json
import socket
import time
import urllib.request
from datetime import date, datetime, timedelta
from enum import Enum
import logging

from PIL import Image, ImageDraw, ImageFont

from weightloss_gadget import google_sheets_interface
from weightloss_gadget.gui_actions import GuiActions
import weightloss_gadget.led_patterns as led_patterns

SCREEN_WIDTH = 128
SCREEN_HEIGHT = 64


# interface = google_sheets_interface.GoogleSheetsInterface(
#     client_secret_file=r'C:\Users\michael.meer\PycharmProjects\WeightlossGadget\client_secret_1082141044520-n0cg7u76fd8pvvagh929o91538u1val1.apps.googleusercontent.com.json',
#     application_name='dailycalories',
#     sheet_id='1VHbeWIq21ib7MndwwCHRon52of1MI4z9RVproZ_kpCk'
# )

fnt = ImageFont.truetype(r'../resources/Roboto-Bold.ttf', 14)


class Color(Enum):
    BLACK = 0
    WHITE = 1


class AbstractScreen(object):
    def __init__(self, controller, config):
        self.controller = controller
        self.config = config
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

    def does_need_update(self):
        return False


class WatchScreen(AbstractScreen):
    def __init__(self, controller, config):
        super().__init__(controller, config)
        self.counter = 0

    def does_need_update(self):
        if not self.controller.is_led_pattern_set():
            self.controller.set_led_pattern(led_patterns.red_blinking_pattern)
        self.counter += 1
        return self.counter % 5 == 0

    def create_image(self):
        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), 128)
        draw = ImageDraw.Draw(im)

        t = time.localtime()
        time_text = time.strftime("%H:%M:%S", t)
        weekday_text = time.strftime("%A", t)
        date_text = time.strftime('%Y-%m-%d', t)

        draw.text((0, 0), time_text, font=fnt)
        draw.text((0, 18), weekday_text, font=fnt)
        draw.text((0, 36), date_text, font=fnt)
        self.logger.debug("time used in picture: %s" % time_text)
        del draw
        return im

class IpAddressScreen(AbstractScreen):
    def __init__(self, controller, config):
        super().__init__(controller, config)
        self.counter = 0
       
    def does_need_update(self):
        self.counter += 1
        return self.counter <= 1

    def create_image(self):
        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color = 0)
        draw = ImageDraw.Draw(im)
        ip_address = socket.gethostbyname(socket.gethostname())
        hostname = socket.gethostname()
        draw.text((0, 0), ip_address, font=fnt, fill=1)
        draw.text((0, 20), hostname, font=fnt, fill=1)

        del draw
        return im


class WeatherScreen(AbstractScreen):
    zip_code_query_template = "http://api.openweathermap.org/data/2.5/weather?appid={API_KEY}&zip={zip_code},{country_code}&units=metric"

    """
    Find black / white weather icons here:
    https://erikflowers.github.io/weather-icons/
    
    """
    def __init__(self, controller, config):
        super().__init__(controller, config)
        self.api_key = self.config['api_key']
        self.zip_code = self.config['zip_code']
        self.country_code = self.config['country_code']
        self.current_weather_data = self.fetch_current_data()

    def fetch_current_data(self):
        zip_code_query = self.zip_code_query_template.format(
            API_KEY=self.api_key,
            zip_code=self.zip_code,
            country_code=self.country_code)
        self.logger.debug("Weather Query: %s"%zip_code_query)

        url_request = urllib.request.urlopen(zip_code_query)
        raw_content = url_request.read()
        encoding = url_request.info().get_content_charset('utf-8')
        parsed_weather_data = json.loads(raw_content.decode(encoding))
        self.logger.debug("Current Weather Data: %s", parsed_weather_data)
        return parsed_weather_data

    def create_image(self):
        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color = 0)
        draw = ImageDraw.Draw(im)

        current_temperature = self.current_weather_data['main']['temp']
        city = self.current_weather_data['name']
        sunrise_timestamp = self.current_weather_data['sys']['sunrise']
        sunrise = datetime.fromtimestamp(sunrise_timestamp)
        sunset_timestamp = self.current_weather_data['sys']['sunset']
        sunset = datetime.fromtimestamp(sunset_timestamp)

        temperature = "%.1f C"%current_temperature
        draw.text((0, 0), city, font=fnt, fill=1)
        draw.text((0, 15), temperature, font=fnt, fill=1)

        del draw
        return im


class WeightChartScreen(AbstractScreen):
    def __init__(self, controller, config):
        super().__init__(controller, config)
        self.data_points = [66.6,
            66.5,
            66.4,
            66.3,
            66.2,
            66.1,
            66.0,
            65.9,
            65.8,
            65.7,
            65.6,
            65.5,
            65.4,
            65.3,
            65.2,
            65.1,
            65.0,
            64.9,
            64.8,
            64.7,
            64.6,
            64.6,
            64.6,
            64.9,
            64.3,
            64.1,
            64.0,
            63.9,
            63.8,
            63.7,
            63.6,
        ]

    def create_image(self):
        FG = 0
        BG = 1
        im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color=BG)
        draw = ImageDraw.Draw(im)

        min_weight = min(self.data_points)
        max_weight = max(self.data_points)
        number_of_elements = len(self.data_points)
        self.logger.info("min_weight %i, max_weight %i, number_of_elements %i", min_weight, max_weight, number_of_elements)

        """
        30 elements, 128 pixels
        """
        x_multiplicator = SCREEN_WIDTH // number_of_elements

        lines = [(x*x_multiplicator, SCREEN_HEIGHT - (current_weight - min_weight) / (max_weight - min_weight) * SCREEN_HEIGHT) for x, current_weight in enumerate(self.data_points)]

        draw.line(lines, fill=FG)
        """
        0   max_y
        
        
        64  min_y
        
        
        Bsp: max_y = 90, min_y = 60, current = 70.
        
        70-60 /90-60  = 10/30 = 1/3 * 64 = 21.3 => 64 - 21.3 = 42.7
        screen_height - (current_y - min_y) / (max_y - min_y) * screen_height
        
        """

        del draw
        return im


class WeightInputScreen(AbstractScreen):
    """
    Here's what should be shown in the initial version
    
    Regular screen
    --------------
    - Name
    - Last input date
    - Last weight
    - Trend
    
    Input Screen
    ------------
    - Name
    - Blinking Weight
    
    """
    def __init__(self, controller, config):
        super().__init__(controller, config)
        self.person = self.config['person']
        self.update_frequency = 0.5
        self.counter = 0
        self.input_mode = False

        self.refresh_current_data()

    def refresh_current_data(self):
        last_updates = interface.read_last_updates(self.person)
        self.current_weight = last_updates["Latest Measured Weight"]
        self.last_date = last_updates["Last Set Day"]
        self.current_trend_weight = last_updates["Latest Trend Weight"]
        self.current_variance = last_updates["Latest Variance"]

    def does_need_update(self):
        self.counter += 1
        return self.counter % 2 == 0

    def formatted_last_date(self):
        today = date.today()
        yesterday = today - timedelta(days=1)
        if self.last_date == today.isoformat():
            return "Today"
        elif self.last_date == yesterday.isoformat():
            return "Yesterday"
        else:
            return self.last_date

    def create_image(self):
        if self.input_mode:
            FG = 1
            BG = 0
            im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color=BG)
            draw = ImageDraw.Draw(im)
            draw.text((0, 0), self.person, font=fnt, fill=FG)
            weight_str = "Weight: %5.1f"%self.current_weight
            self.logger.debug("Counter: %i", self.counter)
            if self.input_mode and self.counter%3 == 0:
                weight_str = weight_str[:-1]+' '
            draw.text((30, 20), weight_str, font=fnt, fill=FG)

        else:
            FG = 0
            BG = 1
            im = Image.new('1', (SCREEN_WIDTH, SCREEN_HEIGHT), color=BG)
            draw = ImageDraw.Draw(im)

            weight_str = "Weight: %5.1f" % self.current_weight
            variance_str = "Trend: %5.1f" % self.current_variance
            draw.text((0, 0), self.person, font=fnt, fill=FG)
            draw.text((0, 14), self.formatted_last_date(), font=fnt, fill=FG)
            draw.text((0, 28), weight_str, font=fnt, fill=FG)
            draw.text((0, 42), variance_str, font=fnt, fill=FG)

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
            interface.write_weight(self.person, self.current_weight)
            self.refresh_current_data()
            self.set_input_mode(False)
        elif input.value == GuiActions.LEFT.value:
            self.current_weight += -0.1
        elif input.value == GuiActions.RIGHT.value:
            self.current_weight += 0.1
