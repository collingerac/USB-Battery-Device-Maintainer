#!/usr/bin/env python3
"""
USB Battery Device Maintainer
Version: 0.1.0-alpha
Author: Alex
License: MIT
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.animation import Animation
from kivy.core.text import LabelBase
import subprocess


def control_usb_port(location, action):
    """Control USB port using uhubctl command-line tool"""
    try:
        subprocess.run(['uhubctl', '-l', location, '-a', action], 
                      check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error controlling USB port: {e}")
        return False

# Example: Turn off port 2 on bus 1-1
control_usb_port('1-1', 'off')  # or 'on' to enable
from datetime import datetime, timedelta
import json
import os

# New: For INA219 (install: sudo pip3 install adafruit-circuitpython-ina219)
# Note: These libraries only work on Raspberry Pi/Linux with actual hardware
try:
    import board
    import busio
    from adafruit_ina219 import INA219
    i2c = busio.I2C(board.SCL, board.SDA)
    ina_sensors = [
        INA219(i2c, addr=0x40),  # Port 1
        INA219(i2c, addr=0x41),  # Port 2
        INA219(i2c, addr=0x44),  # Port 3
        INA219(i2c, addr=0x45)   # Port 4
    ]
    use_ina219 = True
    print("INA219 sensors initialized successfully")
except Exception as e:
    use_ina219 = False
    ina_sensors = []
    print(f"INA219 not available (running on Windows or hardware not connected): {type(e).__name__}")

# Register Boxicons font - use absolute path relative to script location
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(SCRIPT_DIR, 'fonts', 'boxicons.ttf')

try:
    LabelBase.register(name='boxicons', fn_regular=FONT_PATH)
    print(f"Boxicons font loaded successfully from: {FONT_PATH}")
except Exception as e:
    print(f"Warning: Could not load boxicons font from {FONT_PATH}: {e}")
    print("App will continue but icon glyphs may not display correctly.")

# Configure for Argon POD display (320x240)
Config.set('graphics', 'width', '320')
Config.set('graphics', 'height', '240')
Config.set('graphics', 'fullscreen', '0')
Config.set('graphics', 'borderless', '1')
Config.set('graphics', 'window_state', 'visible')
Config.set('graphics', 'maxfps', '10')

# Force software rendering for headless with display
Config.set('graphics', 'multisamples', '0')
os.environ['KIVY_GL_BACKEND'] = 'sdl2'

CONFIG_FILE = '/home/pi/config.json'

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        BUS = config.get('BUS', 1)
        PORT = config.get('PORT', 0)
        CHARGE_MINUTES = config.get('CHARGE_MINUTES', 45)
        CYCLE_DAYS = config.get('CYCLE_DAYS', 150)
        BRIGHTNESS = config.get('BRIGHTNESS', 50)
else:
    BUS = 1
    PORT = 0
    CHARGE_MINUTES = 45
    CYCLE_DAYS = 150
    BRIGHTNESS = 50

ADC_PIN = 26
use_ads1115 = False
try:
    from adafruit_ads1x15.ads1115 import ADS1115
    ads = ADS1115(i2c)  # Reuse i2c from above
    use_ads1115 = True
    print("ADS1115 ADC initialized successfully")
except Exception as e:
    print(f"ADS1115 not available (running on Windows or hardware not connected): {type(e).__name__}")
    pass

next_charge = datetime.now() + timedelta(days=CYCLE_DAYS)
charging = False

def read_battery_voltage():
    if use_ads1115:
        raw = ads.read_adc(0) * 4.096 / 32768 * 2
        return round(raw, 3)
    return 0.0

def voltage_to_percent(v):
    if v < 3.2: return 0
    if v < 3.6: return int(10 + (v - 3.2) * 225)
    if v < 4.0: return int(90 + (v - 3.6) * 25)
    if v >= 4.2: return 100
    return int(95 + (v - 4.0) * 25)

# New: Read per-port voltages from INA219
def read_port_voltages():
    voltages = []
    for ina in ina_sensors:
        try:
            v = round(ina.bus_voltage, 2)
            voltages.append(f"{v}V")
        except:
            voltages.append("--")
    return " | ".join(voltages) if voltages else "--"

def save_config():
    """Save configuration to file"""
    config_data = {
        'BUS': BUS,
        'PORT': PORT,
        'CHARGE_MINUTES': CHARGE_MINUTES,
        'CYCLE_DAYS': CYCLE_DAYS,
        'BRIGHTNESS': BRIGHTNESS
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=2)

def set_brightness(value):
    """Set Argon POD display brightness (0-100)"""
    try:
        subprocess.run(['argonpod-config', f'--brightness={value}'], 
                      check=True, capture_output=True)
        return True
    except:
        print(f"Could not set brightness (Argon POD may not be installed)")
        return False

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=50)
        self.spinner = Label(text='\uf1ce', font_name='boxicons', font_size=80, color=(1,1,1,1))
        self.message = Label(text="Loading...", font_size='24sp', color=(1,1,1,1))
        layout.add_widget(self.spinner)
        layout.add_widget(self.message)
        self.add_widget(layout)

        self.anim = Animation(opacity=0.3, duration=0.8, t='in_out_sine') + Animation(opacity=1, duration=0.8, t='in_out_sine')
        self.anim.repeat = True
        self.anim.start(self.spinner)

        Clock.schedule_once(self.go_to_main, 5)
        self.bind(on_touch_down=self.go_to_main)

    def go_to_main(self, *args):
        self.anim.stop(self.spinner)
        self.manager.current = 'main'

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=5)

        self.status = Label(text="Idle", font_size='38sp', color=(0,1,0,1), size_hint_y=None, height=45)
        self.battery_label = Label(text="Battery: --%", font_size='36sp', color=(0,1,1,1), size_hint_y=None, height=45)
        # New: Per-port voltage label
        self.ports_label = Label(text="Ports: --", font_size='24sp', color=(0.9,0.9,0.9,1), size_hint_y=None, height=30)
        self.icon = Label(text='\uf240', font_name='boxicons', font_size=100, color=(0,1,0,1), size_hint_y=None, height=100)

        self.next_text = Label(text="Next charge in", font_size='22sp', color=(0.9,0.9,0.9,1), size_hint_y=None, height=30)
        self.countdown = Label(text="...", font_size='34sp', bold=True, color=(1,1,0,1), size_hint_y=None, height=45)

        self.touch_button = Button(text="FORCE CHARGE NOW", font_size='30sp', background_color=(0.2,0.6,1,0.8), size_hint_y=None, height=70)
        self.touch_button.bind(on_press=self.on_touch)

        self.settings_button = Button(text="Settings", font_size='24sp', background_color=(0.3,0.3,0.3,1), size_hint_y=None, height=50)
        self.settings_button.bind(on_press=self.go_to_settings)

        self.layout.add_widget(self.status)
        self.layout.add_widget(self.battery_label)
        self.layout.add_widget(self.ports_label)  # New addition
        self.layout.add_widget(self.icon)
        self.layout.add_widget(self.next_text)
        self.layout.add_widget(self.countdown)
        self.layout.add_widget(self.touch_button)
        self.layout.add_widget(self.settings_button)

        self.add_widget(self.layout)

        Clock.schedule_interval(self.update_display, 30)
        Clock.schedule_once(self.start_cycle, 10)

        self.battery_anim = None

    def update_display(self, dt):
        v = read_battery_voltage()
        percent = voltage_to_percent(v) if v > 0.5 else 0
        self.battery_label.text = f"Battery: {percent}%"
        if percent < 20:
            self.battery_label.color = (1,0.3,0.3,1)
        elif percent < 50:
            self.battery_label.color = (1,1,0,1)
        else:
            self.battery_label.color = (0,1,1,1)

        # New: Update per-port voltages
        self.ports_label.text = f"Ports: {read_port_voltages()}"

        if not charging and datetime.now() < next_charge:
            delta = next_charge - datetime.now()
            d = delta.days
            h, rem = divmod(delta.seconds, 3600)
            m = rem // 60
            self.countdown.text = f"{d}d {h}h {m}m"

    def on_touch(self, instance):
        global charging, next_charge
        if charging:
            control_usb_port(f'{BUS}-{BUS}', 'off')
            charging = False
            self.status.color = (0,1,0,1)
            self.icon.color = (0,1,0,1)
            self.touch_button.text = "FORCE CHARGE NOW"
            self.touch_button.background_color = (0.2,0.6,1,0.8)
            next_charge = datetime.now() + timedelta(minutes=10)
            if self.battery_anim:
                self.battery_anim.stop(self.icon)
        else:
            charging = True
            control_usb_port(f'{BUS}-{BUS}', 'on')
            self.status.text = "CHARGING (manual)"
            self.icon.color = (1,1,0,1)
            self.touch_button.text = "STOP CHARGING"
            self.touch_button.background_color = (1,0.2,0.2,0.9)
            self.countdown.text = f"{CHARGE_MINUTES} min"
            Clock.schedule_once(self.auto_stop, CHARGE_MINUTES * 60)
            self.battery_anim = Animation(font_size=105, duration=0.4, t='in_out_sine') + Animation(font_size=100, duration=0.4, t='in_out_sine')
            self.battery_anim.repeat = True
            self.battery_anim.start(self.icon)

    def auto_stop(self, dt):
        global charging, next_charge
        control_usb_port(f'{BUS}-{BUS}', 'off')
        charging = False
        self.status.text = "Idle"
        self.status.color = (0,1,0,1)
        self.icon.color = (0,1,0,1)
        self.touch_button.text = "FORCE CHARGE NOW"
        self.touch_button.background_color = (0.2,0.6,1,0.8)
        next_charge = datetime.now() + timedelta(days=CYCLE_DAYS)
        self.update_display(0)
        if self.battery_anim:
            self.battery_anim.stop(self.icon)

    def start_cycle(self, dt):
        if not charging:
            self.on_touch(None)

    def go_to_settings(self, instance):
        self.manager.current = 'settings'

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use ScrollView for better fit on small screen
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.slider import Slider
        scroll = ScrollView(size_hint=(1, 1))
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=8, size_hint_y=None)
        self.layout.bind(minimum_height=self.layout.setter('height'))

        # Title
        title = Label(text="Settings", font_size='32sp', bold=True, size_hint_y=None, height=40)
        self.layout.add_widget(title)

        # USB Bus setting
        bus_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        bus_label = Label(text="USB Bus:", font_size='24sp', size_hint_x=0.5)
        self.bus_value = Label(text=str(BUS), font_size='24sp', size_hint_x=0.3)
        bus_minus = Button(text="-", font_size='24sp', size_hint_x=0.3, background_color=(1,0.2,0.2,0.9))
        bus_minus.bind(on_press=self.decrement_bus)
        bus_plus = Button(text="+", font_size='24sp', size_hint_x=0.3, background_color=(0.2,0.8,0.2,1))
        bus_plus.bind(on_press=self.increment_bus)
        bus_row.add_widget(bus_label)
        bus_row.add_widget(self.bus_value)
        bus_row.add_widget(bus_minus)
        bus_row.add_widget(bus_plus)

        # USB Port setting
        port_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        port_label = Label(text="USB Port:", font_size='24sp', size_hint_x=0.5)
        self.port_value = Label(text=str(PORT), font_size='24sp', size_hint_x=0.3)
        port_minus = Button(text="-", font_size='24sp', size_hint_x=0.3, background_color=(1,0.2,0.2,0.9))
        port_minus.bind(on_press=self.decrement_port)
        port_plus = Button(text="+", font_size='24sp', size_hint_x=0.3, background_color=(0.2,0.8,0.2,1))
        port_plus.bind(on_press=self.increment_port)
        port_row.add_widget(port_label)
        port_row.add_widget(self.port_value)
        port_row.add_widget(port_minus)
        port_row.add_widget(port_plus)

        # Charge Duration setting
        charge_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        charge_label = Label(text="Charge (min):", font_size='24sp', size_hint_x=0.5)
        self.charge_value = Label(text=str(CHARGE_MINUTES), font_size='24sp', size_hint_x=0.3)
        charge_minus = Button(text="-", font_size='24sp', size_hint_x=0.3, background_color=(1,0.2,0.2,0.9))
        charge_minus.bind(on_press=self.decrement_charge)
        charge_plus = Button(text="+", font_size='24sp', size_hint_x=0.3, background_color=(0.2,0.8,0.2,1))
        charge_plus.bind(on_press=self.increment_charge)
        charge_row.add_widget(charge_label)
        charge_row.add_widget(self.charge_value)
        charge_row.add_widget(charge_minus)
        charge_row.add_widget(charge_plus)

        # Cycle Days setting
        cycle_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        cycle_label = Label(text="Cycle (days):", font_size='24sp', size_hint_x=0.5)
        self.cycle_value = Label(text=str(CYCLE_DAYS), font_size='24sp', size_hint_x=0.3)
        cycle_minus = Button(text="-", font_size='24sp', size_hint_x=0.3, background_color=(1,0.2,0.2,0.9))
        cycle_minus.bind(on_press=self.decrement_cycle)
        cycle_plus = Button(text="+", font_size='24sp', size_hint_x=0.3, background_color=(0.2,0.8,0.2,1))
        cycle_plus.bind(on_press=self.increment_cycle)
        cycle_row.add_widget(cycle_label)
        cycle_row.add_widget(self.cycle_value)
        cycle_row.add_widget(cycle_minus)
        cycle_row.add_widget(cycle_plus)

        # Brightness setting with slider
        brightness_container = BoxLayout(orientation='vertical', spacing=5, size_hint_y=None, height=70)
        brightness_header = BoxLayout(orientation='horizontal', size_hint_y=None, height=30)
        brightness_label = Label(text="Brightness:", font_size='24sp', size_hint_x=0.6)
        self.brightness_value = Label(text=f"{BRIGHTNESS}%", font_size='24sp', size_hint_x=0.4)
        brightness_header.add_widget(brightness_label)
        brightness_header.add_widget(self.brightness_value)
        
        # Slider
        self.brightness_slider = Slider(min=10, max=100, value=BRIGHTNESS, step=10, size_hint_y=None, height=30)
        self.brightness_slider.bind(value=self.on_brightness_change)
        
        brightness_container.add_widget(brightness_header)
        brightness_container.add_widget(self.brightness_slider)

        # Buttons
        self.save_button = Button(text="Save & Back", font_size='26sp', background_color=(0.2,0.8,0.2,1), size_hint_y=None, height=50)
        # Add all rows
        self.layout.add_widget(bus_row)
        self.layout.add_widget(port_row)
        self.layout.add_widget(charge_row)
        self.layout.add_widget(cycle_row)
        self.layout.add_widget(brightness_container)
        self.layout.add_widget(self.save_button)
        self.layout.add_widget(brightness_row)
        self.layout.add_widget(self.save_button)

        scroll.add_widget(self.layout)
        self.add_widget(scroll)

    def increment_bus(self, instance):
        global BUS
        if BUS < 9:
            BUS += 1
            self.bus_value.text = str(BUS)

    def decrement_bus(self, instance):
        global BUS
        if BUS > 1:
            BUS -= 1
            self.bus_value.text = str(BUS)

    def increment_port(self, instance):
        global PORT
        if PORT < 9:
            PORT += 1
            self.port_value.text = str(PORT)

    def decrement_port(self, instance):
        global PORT
        if PORT > 0:
            PORT -= 1
            self.port_value.text = str(PORT)

    def increment_charge(self, instance):
        global CHARGE_MINUTES
        if CHARGE_MINUTES < 120:
            CHARGE_MINUTES += 5
            self.charge_value.text = str(CHARGE_MINUTES)

    def decrement_charge(self, instance):
        global CHARGE_MINUTES
        if CHARGE_MINUTES > 10:
            CHARGE_MINUTES -= 5
            self.charge_value.text = str(CHARGE_MINUTES)

    def increment_cycle(self, instance):
        global CYCLE_DAYS
        if CYCLE_DAYS < 365:
            CYCLE_DAYS += 5
            self.cycle_value.text = str(CYCLE_DAYS)

    def decrement_cycle(self, instance):
        global CYCLE_DAYS
        if CYCLE_DAYS > 1:
            CYCLE_DAYS -= 5
            self.cycle_value.text = str(CYCLE_DAYS)

    def on_brightness_change(self, instance, value):
        """Handle brightness slider changes"""
        global BRIGHTNESS
        BRIGHTNESS = int(value)
        self.brightness_value.text = f"{BRIGHTNESS}%"
        set_brightness(BRIGHTNESS)

    def save_and_back(self, instance):
        save_config()
        self.manager.current = 'main'

class BatteryApp(App):
    def build(self):
        Window.clearcolor = (0.13, 0.13, 0.13, 1)
        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.current = 'splash'
        return sm

if __name__ == '__main__':
    BatteryApp().run()