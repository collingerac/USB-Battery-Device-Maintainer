#!/usr/bin/env python3

APP_NAME = "USB Battery Device Maintainer"
APP_VERSION = "0.1.3-alpha"
APP_AUTHOR = "Alex"
APP_LICENSE = "MIT"

DEBUG_TOUCH = True  # Set to True for extra touch debug output
# Set environment variables BEFORE importing Kivy
import os
import subprocess

# Detect if running on Argon POD before configuring display
def detect_argon_pod_early():
    """Early detection of Argon POD hardware"""
    try:
        # Check for argononed service
        if subprocess.run(['systemctl', 'is-active', 'argononed'], 
                         capture_output=True).returncode == 0:
            return True
        # Check for argonone-daemon
        if subprocess.run(['systemctl', 'is-active', 'argonone-daemon'], 
                         capture_output=True).returncode == 0:
            return True
        # Check for /dev/fb1 display
        if os.path.exists('/dev/fb1'):
            return True
        return False
    except:
        return False

IS_ARGON_POD = detect_argon_pod_early()

# Configure environment based on hardware
if IS_ARGON_POD:
    print("=== Configuring for Argon POD (320x240 fixed) ===")
    # os.environ['DISPLAY'] = ':99'  # Commented out to run on native framebuffer
    os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0'
else:
    print("=== Configuring for general use (resizable window) ===")

os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONSOLELOG'] = '1'  
os.environ['KIVY_WINDOW'] = 'sdl2'
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
os.environ['KIVY_CLIPBOARD'] = 'dummy'

# Configure Kivy BEFORE any other Kivy imports
from kivy.config import Config

if IS_ARGON_POD:
    # Fixed size for Argon POD display
    Config.set('graphics', 'width', '320')
    Config.set('graphics', 'height', '240')
    Config.set('graphics', 'fullscreen', '0')
    Config.set('graphics', 'borderless', '1')
    Config.set('graphics', 'resizable', '0')
    Config.set('graphics', 'maxfps', '10')
else:
    # Resizable window for other systems
    Config.set('graphics', 'width', '800')
    Config.set('graphics', 'height', '600')
    Config.set('graphics', 'fullscreen', '0')
    Config.set('graphics', 'borderless', '0')
    Config.set('graphics', 'resizable', '1')
    Config.set('graphics', 'maxfps', '60')

Config.set('graphics', 'window_state', 'visible')
Config.set('graphics', 'multisamples', '0')
Config.write()

from kivy.app import App
from kivy.input.providers.hidinput import HIDInputMotionEventProvider
from kivy.base import EventLoop
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.animation import Animation
from kivy.core.text import LabelBase
import subprocess
from kivy.uix.popup import Popup
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Ellipse

# Try to import GPIO for physical buttons (Argon POD)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("GPIO not available - physical buttons disabled")
    GPIO_AVAILABLE = False

# Try to import GPIO for physical buttons (Argon POD)
try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    print("GPIO not available - physical buttons disabled")
    GPIO_AVAILABLE = False


def is_argon_pod():
    """Detect if running on Argon POD hardware"""
    try:
        # Check if argonone service exists (Argon ONE/POD specific)
        result = subprocess.run(
            ['systemctl', 'is-active', 'argononed'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Argon POD detected (argononed service active)")
            return True
        
        # Check for Argon ONE daemon as fallback
        result = subprocess.run(
            ['systemctl', 'is-active', 'argonone-daemon'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("✓ Argon POD detected (argonone-daemon service active)")
            return True
            
        # Check if /dev/fb1 exists (Argon POD display)
        if os.path.exists('/dev/fb1'):
            print("✓ Argon POD display detected (/dev/fb1)")
            return True
            
        print("✗ Not running on Argon POD hardware")
        return False
    except Exception as e:
        print(f"✗ Error detecting Argon POD: {e}")
        return False


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

# Argon POD button GPIO pins (BCM numbering)
BUTTON_PINS = {
    'BUTTON1': 26,  # Button 1 (far left)
    'BUTTON2': 21,  # Button 2 (middle-left)
    'BUTTON3': 20,  # Button 3 (middle-right)
    'BUTTON4': 16   # Button 4 (far right/settings)
}

def setup_gpio_buttons(callback_handler):
    """Setup GPIO pins for physical buttons using polling"""
    if not GPIO_AVAILABLE:
        print("✗ GPIO not available (RPi.GPIO not imported)")
        return False
    
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        print(f"Setting up GPIO buttons on pins: {list(BUTTON_PINS.values())}")
        for button_name, pin in BUTTON_PINS.items():
            print(f"  Configuring {button_name} on GPIO {pin}")
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            # Test current state
            state = GPIO.input(pin)
            print(f"    Current state: {state} (1=not pressed, 0=pressed)")
        
        print(f"✓ GPIO buttons configured for polling (another service has edge detection)")
        return True
    except Exception as e:
        print(f"✗ Failed to setup GPIO buttons: {e}")
        return False

def cleanup_gpio():
    """Cleanup GPIO on exit"""
    if GPIO_AVAILABLE:
        try:
            GPIO.cleanup()
        except:
            pass

from datetime import datetime, timedelta
import json

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


# Register Boxicons font - always use fonts folder inside script directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(SCRIPT_DIR, 'fonts', 'boxicons.ttf')

if not os.path.exists(FONT_PATH):
    print(f"ERROR: Boxicons font not found at: {FONT_PATH}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Script directory: {SCRIPT_DIR}")
    if os.path.exists(os.path.join(SCRIPT_DIR, 'fonts')):
        print(f"Fonts directory contents: {os.listdir(os.path.join(SCRIPT_DIR, 'fonts'))}")
else:
    print(f"Found boxicons font at: {FONT_PATH}")

try:
    LabelBase.register(name='boxicons', fn_regular=FONT_PATH)
    print(f"✓ Boxicons font loaded successfully from: {FONT_PATH}")
except Exception as e:
    print(f"✗ Warning: Could not load boxicons font from {FONT_PATH}: {e}")
    print("App will continue but icon glyphs may not display correctly.")
    print("To fix: Ensure boxicons.ttf is in the fonts/ subdirectory next to battery_maintainer.py")

CONFIG_FILE = '/home/pi/config.json'
# Config defaults
IP_ADDRESS = '192.168.1.100'
SSH_ENABLED = False
STATIC_IP = False
TARGET_CHARGE_PERCENT = 80  # Target charge percentage for connected devices
ENABLE_VOLTAGE_MONITORING = True  # Monitor voltage and stop at target percentage

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
        BUS = config.get('BUS', 1)
        PORT = config.get('PORT', 0)
        CHARGE_MINUTES = config.get('CHARGE_MINUTES', 45)
        CYCLE_DAYS = config.get('CYCLE_DAYS', 150)
        BRIGHTNESS = config.get('BRIGHTNESS', 50)
        IP_ADDRESS = config.get('IP_ADDRESS', IP_ADDRESS)
        SSH_ENABLED = config.get('SSH_ENABLED', SSH_ENABLED)
        STATIC_IP = config.get('STATIC_IP', STATIC_IP)
        TARGET_CHARGE_PERCENT = config.get('TARGET_CHARGE_PERCENT', 80)
        ENABLE_VOLTAGE_MONITORING = config.get('ENABLE_VOLTAGE_MONITORING', True)
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

def read_port_current(port_index=0):
    """Read current draw from specific USB port (in mA)"""
    if use_ina219 and port_index < len(ina_sensors):
        try:
            current = ina_sensors[port_index].current
            return abs(current)  # Return absolute value
        except:
            return 0.0
    return 0.0

def estimate_charge_level(port_index=0):
    """Estimate charge level based on voltage and current draw"""
    if not use_ina219 or port_index >= len(ina_sensors):
        return None
    
    try:
        voltage = ina_sensors[port_index].bus_voltage
        current = abs(ina_sensors[port_index].current)
        
        # Typical USB charging profile:
        # - Below 4.0V: Low battery (0-20%)
        # - 4.0-4.15V: Charging (20-80%)
        # - Above 4.15V: Nearly full (80-100%)
        # - Current < 100mA: Trickle/maintenance mode (90-100%)
        
        if current < 100:  # Device is nearly full when current drops below 100mA
            return 95
        elif voltage >= 4.15:
            return 80
        elif voltage >= 4.0:
            return int(20 + ((voltage - 4.0) / 0.15) * 60)
        else:
            return int((voltage / 4.0) * 20)
    except:
        return None

def save_config():
    """Save configuration to file"""
    config_data = {
        'BUS': BUS,
        'PORT': PORT,
        'CHARGE_MINUTES': CHARGE_MINUTES,
        'CYCLE_DAYS': CYCLE_DAYS,
        'BRIGHTNESS': BRIGHTNESS,
        'IP_ADDRESS': IP_ADDRESS,
        'SSH_ENABLED': SSH_ENABLED,
        'STATIC_IP': STATIC_IP,
        'TARGET_CHARGE_PERCENT': TARGET_CHARGE_PERCENT,
        'ENABLE_VOLTAGE_MONITORING': ENABLE_VOLTAGE_MONITORING
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


class OnScreenKeyboard(Popup):
    """Minimal on-screen keyboard popup for touch input.
    Inserts characters into a target `TextInput` and dismisses on ENTER.
    """
    def __init__(self, target=None, **kwargs):
        super().__init__(**kwargs)
        self.title = ''
        self.size_hint = (0.98, 0.45)
        self.auto_dismiss = False
        self.target = target

        # Build layout
        outer = BoxLayout(orientation='vertical', spacing=4, padding=6)

        rows = [
            '1234567890',
            'qwertyuiop',
            'asdfghjkl',
            'zxcvbnm-._@'
        ]

        for r in rows:
            row = BoxLayout(orientation='horizontal', spacing=4, size_hint_y=None, height=40)
            for ch in r:
                btn = Button(text=ch, font_size=20)
                btn.bind(on_press=self._keypress)
                row.add_widget(btn)
            outer.add_widget(row)

        ctrl = BoxLayout(orientation='horizontal', spacing=4, size_hint_y=None, height=48)
        sp = Button(text='SPACE', font_size=18)
        sp.bind(on_press=lambda *_: self._insert(' '))
        bk = Button(text='BACK', font_size=18)
        bk.bind(on_press=lambda *_: self._backspace())
        en = Button(text='ENTER', font_size=18)
        en.bind(on_press=lambda *_: self._enter())
        ctrl.add_widget(sp)
        ctrl.add_widget(bk)
        ctrl.add_widget(en)
        outer.add_widget(ctrl)

        self.content = outer

    def _keypress(self, instance):
        self._insert(instance.text)

    def _insert(self, text):
        if not self.target:
            return
        ti = self.target
        # insert at cursor index
        try:
            pos = ti.cursor_index()
        except Exception:
            pos = len(ti.text)
        s = ti.text or ''
        ti.text = s[:pos] + text + s[pos:]

    def _backspace(self):
        if not self.target:
            return
        ti = self.target
        try:
            pos = ti.cursor_index()
        except Exception:
            pos = len(ti.text)
        if pos == 0:
            return
        s = ti.text or ''
        ti.text = s[:pos-1] + s[pos:]

    def _enter(self):
        try:
            if self.target:
                self.target.focus = False
        except Exception:
            pass
        self.dismiss()

class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transitioned = False  # Prevent repeated transitions
        # Black background
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)
        self.layout = BoxLayout(orientation='vertical', padding=50, spacing=20)
        # App name and version
        self.title_label = Label(text=APP_NAME, font_size='20sp', color=(1,1,1,1), size_hint_y=None, height=40)
        self.version_label = Label(text=f"v{APP_VERSION}", font_size='18sp', color=(0.7,0.7,0.7,1), size_hint_y=None, height=30)
        self.layout.add_widget(self.title_label)
        self.layout.add_widget(self.version_label)
        # Loader icon
        self.spinner = Label(text='\ueb46', font_name='boxicons', font_size='75sp', color=(1,1,1,1))
        self.layout.add_widget(self.spinner)
        self.add_widget(self.layout)
        # Rotation animation for continuous spinning (reliable method)
        from kivy.graphics import Rotate, PushMatrix, PopMatrix
        with self.spinner.canvas.before:
            PushMatrix()
            self.rotate = Rotate(angle=0, origin=self.spinner.center)
        with self.spinner.canvas.after:
            PopMatrix()
        self.spinner.bind(center=self._update_rotation_origin)
        Clock.schedule_interval(self._spin_loader, 1/30)  # 30 FPS

        # Schedule fade and touch-to-skip in __init__ (not every frame)
        Clock.schedule_once(self.fade_and_go_to_main, 20)  # Fade after 20 seconds
        self.bind(on_touch_down=self.go_to_main)

    def _spin_loader(self, dt):
        self.rotate.angle = (self.rotate.angle - 6) % 360  # 6 degrees per frame, spin right

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size
    def _update_rotation_origin(self, instance, value):
        self.rotate.origin = instance.center
    def fade_and_go_to_main(self, *args):
        if self.transitioned:
            return
        from kivy.config import Config
        # Save and boost frame rate for smooth transition
        self._original_maxfps = Config.getint('graphics', 'maxfps')
        Config.set('graphics', 'maxfps', '60')
        Config.write()
        def transition_and_log(*_):
            print('[DEBUG] SplashScreen: transitioning to main screen')
            self.go_to_main(fade_main=True)
        print('[DEBUG] SplashScreen: fade_and_go_to_main called, starting fade animation')
        self.layout.opacity = 1
        anim = Animation(opacity=0, duration=1.0)
        anim.bind(on_complete=transition_and_log)
        anim.start(self.layout)
    def go_to_main(self, fade_main=False, *args):
        if self.transitioned:
            return
        self.transitioned = True
        self.unbind(on_touch_down=self.go_to_main)
        self.manager.current = 'main'
        self.opacity = 1  # Reset opacity so future transitions work
        # Fade in only the main screen's layout for a smooth transition
        if fade_main and self.manager is not None:
            main_screen = self.manager.get_screen('main')
            main_screen.layout.opacity = 0
            anim = Animation(opacity=1, duration=1.0)
            def restore_fps(*_):
                from kivy.config import Config
                if hasattr(self, '_original_maxfps'):
                    Config.set('graphics', 'maxfps', str(self._original_maxfps))
                    Config.write()
            anim.bind(on_complete=restore_fps)
            anim.start(main_screen.layout)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Add black background to prevent white flash during transition
        with self.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0, 0, 0, 1)
            self.rect = Rectangle(size=self.size, pos=self.pos)
            self.bind(size=self._update_rect, pos=self._update_rect)

        self.layout = BoxLayout(orientation='vertical', padding=0, spacing=1)

        self.icon = Label(text='\uecc2', font_name='boxicons', font_size=140, color=(0,1,0,1), size_hint_y=None, height=140)

        self.touch_button = Button(text="FORCE CHARGE NOW", font_size='22sp', background_color=(0.2,0.6,1,0.8), size_hint_y=None, height=50)
        self.touch_button.bind(on_press=self.on_touch)

        # Bottom button bar with icons (works as touch buttons and visual guide for physical buttons)
        self.button_bar = BoxLayout(orientation='horizontal', spacing=2, size_hint_y=None, height=50)
        
        # Button 1 (left) - Info/System details
        self.btn1 = Button(text='\ueb21', font_name='boxicons', font_size='34sp', background_color=(0.2,0.5,0.2,0.9))
        self.btn1.bind(on_press=self.show_info)
        
        # Button 2 - Charge toggle (main action) - Start with correct icon based on state
        btn2_icon = '\uecc2' if charging else '\uecc3'  # Full battery if charging, charging icon if not
        self.btn2 = Button(text=btn2_icon, font_name='boxicons', font_size='34sp', background_color=(0.2,0.6,1,0.9))
        self.btn2.bind(on_press=self.on_touch)  # Same as main charge button
        
        # Button 3 - Back/Home button
        self.btn3 = Button(text='\ueb14', font_name='boxicons', font_size='34sp', background_color=(0.3,0.3,0.3,0.9))
        self.btn3.bind(on_press=self.go_back)
        
        # Button 4 (right) - Settings (toggle)
        self.btn4 = Button(text='\uea6e', font_name='boxicons', font_size='34sp', background_color=(0.3,0.3,0.3,0.9))
        self.btn4.bind(on_press=self.toggle_settings)
        
        self.button_bar.add_widget(self.btn1)
        self.button_bar.add_widget(self.btn2)
        self.button_bar.add_widget(self.btn3)
        self.button_bar.add_widget(self.btn4)

        self.layout.add_widget(self.icon)
        self.layout.add_widget(self.touch_button)
        self.layout.add_widget(self.button_bar)

        self.add_widget(self.layout)

        # Schedule debug output after layout is built
        Clock.schedule_once(self.print_button_positions, 1)

        Clock.schedule_interval(self.update_display, 30)
        Clock.schedule_once(self.start_cycle, 10)

        self.battery_anim = None
        self.battery_anim_event = None
        # Battery charging animation - pulse between full battery and charging (lightning) icons
        self.battery_icons = ['\uecc2', '\uecc3']  # cycle between these two
        self.current_battery_icon = 0
        
        # Setup GPIO buttons only if running on Argon POD
        self.gpio_buttons_enabled = False
        if is_argon_pod():
            print("=== Attempting to setup GPIO buttons ===")
            result = setup_gpio_buttons(self.handle_gpio_button)
            print(f"=== GPIO setup result: {result} ===")
            self.gpio_buttons_enabled = result

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

        # Track button states for polling
        self.button_states = {pin: 1 for pin in BUTTON_PINS.values()}  # 1 = not pressed
        self.last_debug_combo_time = 0

    # GPIO buttons disabled message if not on Argon POD
    # (Moved out of _update_rect to correct indentation)
    # print("=== GPIO buttons disabled (not on Argon POD) ===")
        
        # Track info popup state
        self.info_popup = None
        
        # Start polling GPIO buttons only if enabled and on Argon POD
        if self.gpio_buttons_enabled and GPIO_AVAILABLE:
            Clock.schedule_interval(self.poll_gpio_buttons, 0.1)  # Check every 100ms
    
    def poll_gpio_buttons(self, dt):
        if not GPIO_AVAILABLE or not self.gpio_buttons_enabled:
            return
        for button_name, pin in BUTTON_PINS.items():
            try:
                current_state = GPIO.input(pin)
                if self.button_states[pin] == 1 and current_state == 0:
                    self.handle_gpio_button(pin)
                self.button_states[pin] = current_state
            except Exception as e:
                pass
        # Removed: No button combo launches touch test screen
    
    def handle_gpio_button(self, channel):
        """Handle physical button press from GPIO"""
        print(f"GPIO button pressed on pin {channel}")
        
        # Map GPIO pin to button action
        if channel == BUTTON_PINS['BUTTON1']:
            print("  -> Button 1: Show Info")
            Clock.schedule_once(lambda dt: self.show_info(None), 0)
        elif channel == BUTTON_PINS['BUTTON2']:
            print("  -> Button 2: Toggle Charging")
            Clock.schedule_once(lambda dt: self.on_touch(None), 0)
        elif channel == BUTTON_PINS['BUTTON3']:
            print("  -> Button 3: Back/Home")
            Clock.schedule_once(lambda dt: self.go_back(None), 0)
        elif channel == BUTTON_PINS['BUTTON4']:
            print("  -> Button 4: Toggle Settings")
            Clock.schedule_once(lambda dt: self.toggle_settings(None), 0)
        else:
            print(f"  -> Unknown button on pin {channel}")

    def update_display(self, dt):
        v = read_battery_voltage()
        percent = voltage_to_percent(v) if v > 0.5 else 0
        
        # Check if we should stop charging based on voltage monitoring
        if charging and ENABLE_VOLTAGE_MONITORING:
            charge_level = estimate_charge_level(PORT)
            if charge_level and charge_level >= TARGET_CHARGE_PERCENT:
                print(f"Target charge level reached: {charge_level}% >= {TARGET_CHARGE_PERCENT}%")
                Clock.schedule_once(lambda dt: self.auto_stop(None), 0)

        # Icon color changes based on charging state
        if charging:
            self.icon.color = (1,1,0,1)
        else:
            self.icon.color = (0,1,0,1)

    def animate_battery_icon(self, dt):
        """Cycle through battery charging icons in center icon only"""
        if charging:
            battery_icon = self.battery_icons[self.current_battery_icon]
            self.icon.text = battery_icon  # Only update center icon
            self.current_battery_icon = (self.current_battery_icon + 1) % len(self.battery_icons)
    
    def on_touch(self, instance):
        try:
            global charging, next_charge
            if charging:
                control_usb_port(f'{BUS}-{BUS}', 'off')
                charging = False
                self.icon.text = '\uecc2'  # Reset to base battery icon
                self.icon.color = (0,1,0,1)
                self.btn2.text = '\uecc3'  # Show charging icon (ready to charge)
                self.touch_button.text = "FORCE CHARGE NOW"
                self.touch_button.background_color = (0.2,0.6,1,0.8)
                next_charge = datetime.now() + timedelta(minutes=10)
                # Stop battery charging animation
                if self.battery_anim_event:
                    self.battery_anim_event.cancel()
                    self.battery_anim_event = None
            else:
                charging = True
                control_usb_port(f'{BUS}-{BUS}', 'on')
                self.icon.color = (1,1,0,1)
                self.btn2.text = '\uecc2'  # Show full battery icon (ready to stop)
                self.touch_button.text = "STOP CHARGING"
                self.touch_button.background_color = (1,0.2,0.2,0.9)
                Clock.schedule_once(self.auto_stop, CHARGE_MINUTES * 60)
                # Start battery charging animation - pulse between base and full for charging effect
                self.current_battery_icon = 0
                self.battery_anim_event = Clock.schedule_interval(self.animate_battery_icon, 0.7)
        except Exception as e:
            print(f"Error in on_touch: {e}")

    def auto_stop(self, dt):
        global charging, next_charge
        control_usb_port(f'{BUS}-{BUS}', 'off')
        charging = False
        self.icon.text = '\uecc2'  # Reset to base battery icon
        self.icon.color = (0,1,0,1)
        self.btn2.text = '\uecc3'  # Show charging icon (ready to charge)
        self.touch_button.text = "FORCE CHARGE NOW"
        self.touch_button.background_color = (0.2,0.6,1,0.8)
        next_charge = datetime.now() + timedelta(days=CYCLE_DAYS)
        self.update_display(0)
        # Stop battery charging animation
        if self.battery_anim_event:
            self.battery_anim_event.cancel()
            self.battery_anim_event = None

    def start_cycle(self, dt):
        if not charging:
            self.on_touch(None)

    def go_to_settings(self, instance):
        try:
            self.manager.current = 'settings'
        except Exception as e:
            print(f"Error in go_to_settings: {e}")
    
    def toggle_settings(self, instance):
        """Toggle between settings and main screen, with save prompt if needed."""
        try:
            if self.manager.current == 'settings':
                settings_screen = self.manager.get_screen('settings')
                def do_save(inst):
                    settings_screen.save_and_back(inst)
                def do_discard(inst):
                    self.manager.current = 'main'
                def do_cancel(inst):
                    pass  # Stay on settings
                settings_screen.prompt_save_if_needed(do_save, do_discard, do_cancel)
            else:
                self.manager.current = 'settings'
        except Exception as e:
            print(f"Error in toggle_settings: {e}")
    
    def show_info(self, instance):
        """Button 1 action - Toggle system and battery info popup"""
        try:
            # If popup is already open, close it
            if self.info_popup and self.info_popup._window:
                self.info_popup.dismiss()
                self.info_popup = None
                return
            
            v = read_battery_voltage()
            percent = voltage_to_percent(v) if v > 0.5 else 0
            ports = read_port_voltages()
            
            info_text = f"""Battery: {percent}%\nVoltage: {v:.2f}V\n\nPort Voltages:\n{ports}\n\nVersion: 0.1.3-alpha\n\nStatus: {'Charging' if charging else 'Idle'}"""
            
            content = BoxLayout(orientation='vertical', padding=10, spacing=10)
            info_label = Label(text=info_text, font_size='18sp', halign='left', valign='top')
            info_label.bind(size=info_label.setter('text_size'))
            close_btn = Button(text='Close', size_hint_y=None, height=40, background_color=(0.3,0.3,0.3,1))
            content.add_widget(info_label)
            content.add_widget(close_btn)
            
            self.info_popup = Popup(title='Battery Info', content=content, size_hint=(0.9, 0.8))
            close_btn.bind(on_press=self.info_popup.dismiss)
            close_btn.bind(on_press=lambda x: setattr(self, 'info_popup', None))
            self.info_popup.open()
        except Exception as e:
            print(f"Error in show_info: {e}")
    
    def go_back(self, instance):
        """Button 3 action - Back/Home button"""
        try:
            # Close any open popup first
            if self.info_popup and self.info_popup._window:
                self.info_popup.dismiss()
                self.info_popup = None
                return
            
            # If not on main screen, go back to main
            if self.manager.current != 'main':
                self.manager.current = 'main'
        except Exception as e:
            print(f"Error in go_back: {e}")
    
    def button3_action(self, instance):
        """Button 3 action - could show info or be unused"""
        # Reserved for future use
        pass
    
    def button4_action(self, instance):
        """Button 4 action - Settings (now handled by go_to_settings)"""
        pass
    
    def print_button_positions(self, dt):
        """Debug: Print button positions after layout"""
        print("\n=== Button Positions ===")
        print(f"Screen size: {self.width}x{self.height}")
        print(f"Button 1 (Info):     pos=({self.btn1.x:.0f},{self.btn1.y:.0f}) size=({self.btn1.width:.0f}x{self.btn1.height:.0f})")
        print(f"Button 2 (Charge):   pos=({self.btn2.x:.0f},{self.btn2.y:.0f}) size=({self.btn2.width:.0f}x{self.btn2.height:.0f})")
        print(f"Button 3 (Home):     pos=({self.btn3.x:.0f},{self.btn3.y:.0f}) size=({self.btn3.width:.0f}x{self.btn3.height:.0f})")
        print(f"Button 4 (Settings): pos=({self.btn4.x:.0f},{self.btn4.y:.0f}) size=({self.btn4.width:.0f}x{self.btn4.height:.0f})")
        print("========================\n")
    
    def on_touch_down(self, touch):
        if DEBUG_TOUCH:
            try:
                print(f"\n>>> Touch event: pos=({touch.x:.1f}, {touch.y:.1f}), is_mouse={touch.is_mouse_scrolling if hasattr(touch, 'is_mouse_scrolling') else False}")
                print(f"    Widget: {self}, Window size: {self.width}x{self.height}")
                print(f"    Touch device: {getattr(touch, 'device', 'unknown')}, profile: {getattr(touch, 'profile', 'unknown')}")
                # Print hit-testing for all major widgets
                for name, widget in [('Button 1 (Info)', self.btn1), ('Button 2 (Charge)', self.btn2), ('Button 3 (Home)', self.btn3), ('Button 4 (Settings)', self.btn4), ('Main charge button', self.touch_button)]:
                    if widget.collide_point(touch.x, touch.y):
                        print(f"    -> Detected: {name}")
                # Print normalized coordinates for 320x240 reference
                norm_x = touch.x / self.width if self.width else 0
                norm_y = touch.y / self.height if self.height else 0
                print(f"    Normalized: ({norm_x:.3f}, {norm_y:.3f}) (0-1 range)")
            except Exception as e:
                print(f"Error in on_touch_down debug: {e}")
        return super().on_touch_down(touch)

class SettingsScreen(Screen):
    def has_unsaved_changes(self):
        """Check if any settings have changed from their global values."""
        global BUS, PORT, CHARGE_MINUTES, CYCLE_DAYS, BRIGHTNESS, IP_ADDRESS, SSH_ENABLED, STATIC_IP, TARGET_CHARGE_PERCENT, ENABLE_VOLTAGE_MONITORING
        try:
            if int(self.bus_value.text) != BUS:
                return True
            if int(self.port_value.text) != PORT:
                return True
            if int(self.charge_value.text) != CHARGE_MINUTES:
                return True
            if int(self.cycle_value.text) != CYCLE_DAYS:
                return True
            if int(self.brightness_slider.value) != BRIGHTNESS:
                return True
            if self.ip_input.text.strip() != str(IP_ADDRESS):
                return True
            if bool(self.ssh_switch.active) != bool(SSH_ENABLED):
                return True
            if bool(self.static_switch.active) != bool(STATIC_IP):
                return True
            if int(self.target_value.text.replace('%','')) != TARGET_CHARGE_PERCENT:
                return True
            if bool(self.monitor_switch.active) != bool(ENABLE_VOLTAGE_MONITORING):
                return True
        except Exception as e:
            print(f"Error checking unsaved changes: {e}")
        return False

    def prompt_save_if_needed(self, on_save, on_discard, on_cancel):
        """Show a popup to save/discard/cancel if there are unsaved changes."""
        if not self.has_unsaved_changes():
            on_discard(None)  # No changes, just exit
            return
        box = BoxLayout(orientation='vertical', padding=10, spacing=10)
        label = Label(text="You have unsaved changes. Save before exiting?", font_size='20sp')
        btns = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=50)
        btn_save = Button(text="Save", background_color=(0.2,0.8,0.2,1))
        btn_discard = Button(text="Discard", background_color=(1,0.2,0.2,1))
        btn_cancel = Button(text="Cancel", background_color=(0.3,0.3,0.3,1))
        btns.add_widget(btn_save)
        btns.add_widget(btn_discard)
        btns.add_widget(btn_cancel)
        box.add_widget(label)
        box.add_widget(btns)
        popup = Popup(title="Unsaved Changes", content=box, size_hint=(0.8,0.4))
        btn_save.bind(on_press=lambda inst: (popup.dismiss(), on_save(inst)))
        btn_discard.bind(on_press=lambda inst: (popup.dismiss(), on_discard(inst)))
        btn_cancel.bind(on_press=lambda inst: (popup.dismiss(), on_cancel(inst)))
        popup.open()
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.slider import Slider
        
        # Main layout with tabs at top
        main_layout = BoxLayout(orientation='vertical', padding=0, spacing=0)
        
        # Tab bar at top
        self.tab_bar = BoxLayout(orientation='horizontal', size_hint_y=None, height=40, spacing=2)
        
        # Tab buttons
        self.tab_battery = Button(text="Battery", font_size='18sp', background_color=(0.2,0.6,1,1))
        self.tab_display = Button(text="Display", font_size='18sp', background_color=(0.3,0.3,0.3,0.9))
        self.tab_network = Button(text="Network", font_size='18sp', background_color=(0.3,0.3,0.3,0.9))
        
        self.tab_battery.bind(on_press=lambda x: self.switch_tab('battery'))
        self.tab_display.bind(on_press=lambda x: self.switch_tab('display'))
        self.tab_network.bind(on_press=lambda x: self.switch_tab('network'))
        
        self.tab_bar.add_widget(self.tab_battery)
        self.tab_bar.add_widget(self.tab_display)
        self.tab_bar.add_widget(self.tab_network)
        
        # Content area with scroll
        self.scroll = ScrollView(size_hint=(1, 1))
        self.content_layout = BoxLayout(orientation='vertical', padding=10, spacing=8, size_hint_y=None)
        self.content_layout.bind(minimum_height=self.content_layout.setter('height'))
        
        # Store tab references
        self.current_tab = 'battery'
        self.tabs = {
            'battery': self.tab_battery,
            'display': self.tab_display,
            'network': self.tab_network
        }
        
        # Build initial battery tab
        self.build_battery_tab()
        
        self.scroll.add_widget(self.content_layout)
        main_layout.add_widget(self.tab_bar)
        main_layout.add_widget(self.scroll)
        
        # Save button at bottom
        self.save_button = Button(text="Save & Back", font_size='26sp', background_color=(0.2,0.8,0.2,1), size_hint_y=None, height=50)
        self.save_button.bind(on_press=self.save_and_back)
        main_layout.add_widget(self.save_button)
        
        self.add_widget(main_layout)
    
    def switch_tab(self, tab_name):
        """Switch between settings tabs"""
        # Update tab button colors
        for name, btn in self.tabs.items():
            if name == tab_name:
                btn.background_color = (0.2, 0.6, 1, 1)  # Active color
            else:
                btn.background_color = (0.3, 0.3, 0.3, 0.9)  # Inactive color
        
        # Clear current content
        self.content_layout.clear_widgets()
        
        # Build selected tab content
        self.current_tab = tab_name
        if tab_name == 'battery':
            self.build_battery_tab()
        elif tab_name == 'display':
            self.build_display_tab()
        elif tab_name == 'network':
            self.build_network_tab()
    
    def build_battery_tab(self):
        """Battery-related settings"""
        # USB Bus setting
        bus_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        bus_label = Label(text="USB Bus:", font_size='24sp', size_hint_x=0.45)
        self.bus_value = Label(text=str(BUS), font_size='24sp', size_hint_x=0.2)
        bus_minus = Button(text="-", font_size='24sp', size_hint_x=0.175, background_color=(1,0.2,0.2,0.9))
        bus_minus.bind(on_press=self.decrement_bus)
        bus_plus = Button(text="+", font_size='24sp', size_hint_x=0.175, background_color=(0.2,0.8,0.2,1))
        bus_plus.bind(on_press=self.increment_bus)
        bus_row.add_widget(bus_label)
        bus_row.add_widget(self.bus_value)
        bus_row.add_widget(bus_minus)
        bus_row.add_widget(bus_plus)

        # USB Port setting
        port_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        port_label = Label(text="USB Port:", font_size='24sp', size_hint_x=0.45)
        self.port_value = Label(text=str(PORT), font_size='24sp', size_hint_x=0.2)
        port_minus = Button(text="-", font_size='24sp', size_hint_x=0.175, background_color=(1,0.2,0.2,0.9))
        port_minus.bind(on_press=self.decrement_port)
        port_plus = Button(text="+", font_size='24sp', size_hint_x=0.175, background_color=(0.2,0.8,0.2,1))
        port_plus.bind(on_press=self.increment_port)
        port_row.add_widget(port_label)
        port_row.add_widget(self.port_value)
        port_row.add_widget(port_minus)
        port_row.add_widget(port_plus)

        # Charge Duration setting
        charge_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        charge_label = Label(text="Charge (min):", font_size='24sp', size_hint_x=0.45)
        self.charge_value = Label(text=str(CHARGE_MINUTES), font_size='24sp', size_hint_x=0.2)
        charge_minus = Button(text="-", font_size='24sp', size_hint_x=0.175, background_color=(1,0.2,0.2,0.9))
        charge_minus.bind(on_press=self.decrement_charge)
        charge_plus = Button(text="+", font_size='24sp', size_hint_x=0.175, background_color=(0.2,0.8,0.2,1))
        charge_plus.bind(on_press=self.increment_charge)
        charge_row.add_widget(charge_label)
        charge_row.add_widget(self.charge_value)
        charge_row.add_widget(charge_minus)
        charge_row.add_widget(charge_plus)

        # Cycle Days setting
        cycle_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        cycle_label = Label(text="Cycle (days):", font_size='24sp', size_hint_x=0.45)
        self.cycle_value = Label(text=str(CYCLE_DAYS), font_size='24sp', size_hint_x=0.2)
        cycle_minus = Button(text="-", font_size='24sp', size_hint_x=0.175, background_color=(1,0.2,0.2,0.9))
        cycle_minus.bind(on_press=self.decrement_cycle)
        cycle_plus = Button(text="+", font_size='24sp', size_hint_x=0.175, background_color=(0.2,0.8,0.2,1))
        cycle_plus.bind(on_press=self.increment_cycle)
        cycle_row.add_widget(cycle_label)
        cycle_row.add_widget(self.cycle_value)
        cycle_row.add_widget(cycle_minus)
        cycle_row.add_widget(cycle_plus)

        # Target Charge Percentage setting
        from kivy.uix.switch import Switch
        target_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        target_label = Label(text="Target %:", font_size='24sp', size_hint_x=0.45)
        self.target_value = Label(text=f"{TARGET_CHARGE_PERCENT}%", font_size='24sp', size_hint_x=0.2)
        target_minus = Button(text="-", font_size='24sp', size_hint_x=0.175, background_color=(1,0.2,0.2,0.9))
        target_minus.bind(on_press=self.decrement_target)
        target_plus = Button(text="+", font_size='24sp', size_hint_x=0.175, background_color=(0.2,0.8,0.2,1))
        target_plus.bind(on_press=self.increment_target)
        target_row.add_widget(target_label)
        target_row.add_widget(self.target_value)
        target_row.add_widget(target_minus)
        target_row.add_widget(target_plus)

        # Enable voltage monitoring switch
        monitor_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        monitor_label = Label(text="Voltage Monitor:", font_size='24sp', size_hint_x=0.7)
        self.monitor_switch = Switch(active=bool(ENABLE_VOLTAGE_MONITORING), size_hint_x=0.3)
        monitor_row.add_widget(monitor_label)
        monitor_row.add_widget(self.monitor_switch)

        self.content_layout.add_widget(bus_row)
        self.content_layout.add_widget(port_row)
        self.content_layout.add_widget(charge_row)
        self.content_layout.add_widget(cycle_row)
        self.content_layout.add_widget(target_row)
        self.content_layout.add_widget(monitor_row)
    
    def build_display_tab(self):
        """Display-related settings"""
        from kivy.uix.slider import Slider
        
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
        
        self.content_layout.add_widget(brightness_container)
    
    def build_network_tab(self):
        """Network-related settings"""
        from kivy.uix.textinput import TextInput
        from kivy.uix.switch import Switch
        
        # WiFi SSID input
        wifi_ssid_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        wifi_ssid_label = Label(text="WiFi SSID:", font_size='24sp', size_hint_x=0.5)
        self.wifi_ssid_input = TextInput(text="", font_size='20sp', multiline=False, size_hint_x=0.5, hint_text="Network Name")
        wifi_ssid_row.add_widget(wifi_ssid_label)
        wifi_ssid_row.add_widget(self.wifi_ssid_input)
        
        # WiFi Password input
        wifi_pass_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        wifi_pass_label = Label(text="WiFi Pass:", font_size='24sp', size_hint_x=0.5)
        self.wifi_pass_input = TextInput(text="", font_size='20sp', multiline=False, password=True, size_hint_x=0.5, hint_text="Password")
        wifi_pass_row.add_widget(wifi_pass_label)
        wifi_pass_row.add_widget(self.wifi_pass_input)
        
        # Connect button for WiFi
        wifi_connect_btn = Button(text="Connect to WiFi", font_size='22sp', background_color=(0.2,0.6,1,0.9), size_hint_y=None, height=45)
        wifi_connect_btn.bind(on_press=self.connect_wifi)
        
        # Spacer
        spacer1 = Label(text="", size_hint_y=None, height=10)
        
        # IP address input
        ip_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        ip_label = Label(text="IP Address:", font_size='24sp', size_hint_x=0.5)
        self.ip_input = TextInput(text=str(IP_ADDRESS), font_size='20sp', multiline=False, size_hint_x=0.5)
        ip_row.add_widget(ip_label)
        ip_row.add_widget(self.ip_input)

        # Open on-screen keyboard when an input is focused
        def open_osk(instance, value):
            if value:  # focused
                kb = OnScreenKeyboard(target=instance)
                kb.open()

        self.wifi_ssid_input.bind(focus=open_osk)
        self.wifi_pass_input.bind(focus=open_osk)
        self.ip_input.bind(focus=open_osk)

        # Static IP switch
        static_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        static_label = Label(text="Static IP:", font_size='24sp', size_hint_x=0.5)
        self.static_switch = Switch(active=bool(STATIC_IP), size_hint_x=0.3)
        static_row.add_widget(static_label)
        static_row.add_widget(self.static_switch)

        # SSH enable switch
        ssh_row = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=45)
        ssh_label = Label(text="SSH Enabled:", font_size='24sp', size_hint_x=0.5)
        self.ssh_switch = Switch(active=bool(SSH_ENABLED), size_hint_x=0.3)
        ssh_row.add_widget(ssh_label)
        ssh_row.add_widget(self.ssh_switch)

        self.content_layout.add_widget(wifi_ssid_row)
        self.content_layout.add_widget(wifi_pass_row)
        self.content_layout.add_widget(wifi_connect_btn)
        self.content_layout.add_widget(spacer1)
        self.content_layout.add_widget(ip_row)
        self.content_layout.add_widget(static_row)
        self.content_layout.add_widget(ssh_row)

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

    def increment_target(self, instance):
        global TARGET_CHARGE_PERCENT
        if TARGET_CHARGE_PERCENT < 100:
            TARGET_CHARGE_PERCENT += 5
            self.target_value.text = f"{TARGET_CHARGE_PERCENT}%"

    def decrement_target(self, instance):
        global TARGET_CHARGE_PERCENT
        if TARGET_CHARGE_PERCENT > 50:
            TARGET_CHARGE_PERCENT -= 5
            self.target_value.text = f"{TARGET_CHARGE_PERCENT}%"

    def on_brightness_change(self, instance, value):
        """Handle brightness slider changes"""
        global BRIGHTNESS
        BRIGHTNESS = int(value)
        self.brightness_value.text = f"{BRIGHTNESS}%"
        set_brightness(BRIGHTNESS)
    
    def connect_wifi(self, instance):
        """Connect to WiFi network using wpa_supplicant"""
        ssid = self.wifi_ssid_input.text.strip()
        password = self.wifi_pass_input.text.strip()
        
        if not ssid:
            print("WiFi SSID is required")
            instance.text = "ERROR: SSID Required"
            instance.background_color = (1, 0.2, 0.2, 0.9)
            Clock.schedule_once(lambda dt: self.reset_wifi_button(instance), 2)
            return
        
        if not password:
            print("WiFi password is required")
            instance.text = "ERROR: Password Required"
            instance.background_color = (1, 0.2, 0.2, 0.9)
            Clock.schedule_once(lambda dt: self.reset_wifi_button(instance), 2)
            return
        
        instance.text = "Connecting..."
        instance.background_color = (1, 0.8, 0.2, 0.9)
        
        try:
            # Generate wpa_supplicant config
            result = subprocess.run(
                ['wpa_passphrase', ssid, password],
                capture_output=True,
                text=True,
                check=True
            )
            wpa_config = result.stdout
            
            # Write to wpa_supplicant.conf
            subprocess.run(
                ['sudo', 'tee', '-a', '/etc/wpa_supplicant/wpa_supplicant.conf'],
                input=wpa_config,
                text=True,
                check=True,
                capture_output=True
            )
            
            # Restart networking
            subprocess.run(['sudo', 'wpa_cli', '-i', 'wlan0', 'reconfigure'], check=True, capture_output=True)
            
            print(f"Successfully configured WiFi: {ssid}")
            instance.text = "Connected!"
            instance.background_color = (0.2, 0.8, 0.2, 1)
            Clock.schedule_once(lambda dt: self.reset_wifi_button(instance), 3)
            
            # Clear password field for security
            self.wifi_pass_input.text = ""
            
        except subprocess.CalledProcessError as e:
            print(f"Failed to configure WiFi: {e}")
            instance.text = "Connection Failed"
            instance.background_color = (1, 0.2, 0.2, 0.9)
            Clock.schedule_once(lambda dt: self.reset_wifi_button(instance), 3)
        except Exception as e:
            print(f"Error configuring WiFi: {e}")
            instance.text = "Error"
            instance.background_color = (1, 0.2, 0.2, 0.9)
            Clock.schedule_once(lambda dt: self.reset_wifi_button(instance), 3)
    
    def reset_wifi_button(self, instance):
        """Reset WiFi connect button to default state"""
        instance.text = "Connect to WiFi"
        instance.background_color = (0.2, 0.6, 1, 0.9)

    def save_and_back(self, instance):
        # Persist UI values into globals then save
        global IP_ADDRESS, SSH_ENABLED, STATIC_IP, ENABLE_VOLTAGE_MONITORING
        IP_ADDRESS = self.ip_input.text.strip()
        SSH_ENABLED = bool(self.ssh_switch.active)
        STATIC_IP = bool(self.static_switch.active)
        ENABLE_VOLTAGE_MONITORING = bool(self.monitor_switch.active)

        save_config()

        # Try to enable/disable SSH service if possible (best-effort)
        try:
            if SSH_ENABLED:
                subprocess.run(['sudo', 'systemctl', 'enable', '--now', 'ssh'], check=True, capture_output=True)
                print('SSH enabled')
            else:
                subprocess.run(['sudo', 'systemctl', 'disable', '--now', 'ssh'], check=True, capture_output=True)
                print('SSH disabled')
        except Exception as e:
            print(f"Could not toggle SSH service automatically: {e}")

        self.manager.current = 'main'

class TouchTestScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.canvas_widget = Widget()
        self.add_widget(self.canvas_widget)
        self.info_label = Label(text="Touch anywhere to test mapping", size_hint=(1, None), height=40)
        self.add_widget(self.info_label)

    def on_touch_down(self, touch):
        with self.canvas_widget.canvas:
            Color(1, 0, 0, 1)
            Ellipse(pos=(touch.x-10, touch.y-10), size=(20, 20))
        self.info_label.text = f"Touch at ({int(touch.x)}, {int(touch.y)})"
        return super().on_touch_down(touch)

class BatteryApp(App):
    def build(self):
        # Force window size for Argon POD
        if IS_ARGON_POD:
            Window.size = (320, 240)
            print(f"[DEBUG] Forced Kivy window size to: {Window.size}")
        Window.clearcolor = (0.13, 0.13, 0.13, 1)
        Clock.schedule_once(self._check_window_size, 2)
        if IS_ARGON_POD:
            try:
                provider = HIDInputMotionEventProvider('touchscreen', '/dev/input/event1')
                provider.invert_y = 0
                EventLoop.add_input_provider(provider)
                provider.start()
                print("✓ Registered touch input: /dev/input/event1 (Y-inverted)")
            except Exception as e:
                print(f"✗ Could not register touch input: {e}")
        else:
            print("✓ Using default mouse/touch input (not on Argon POD)")
        from kivy.uix.screenmanager import NoTransition
        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(SettingsScreen(name='settings'))
        sm.add_widget(TouchTestScreen(name='touchtest'))
        sm.current = 'splash'
        print("[DEBUG] Splash screen activated on startup.")
        # Optionally block input until splash is done (handled by fade_and_go_to_main)
        return sm

    def _check_window_size(self, dt):
        w, h = Window.size
        if IS_ARGON_POD and (w != 320 or h != 240):
            print(f"WARNING: Window size is {w}x{h}, expected 320x240 for Argon POD. Touch mapping may be incorrect!")
    
    def on_stop(self):
        """Cleanup GPIO when app closes"""
        cleanup_gpio()
        return True

if __name__ == '__main__':
    try:
        BatteryApp().run()
    finally:
        cleanup_gpio()