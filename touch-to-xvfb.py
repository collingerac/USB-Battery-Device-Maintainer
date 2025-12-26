#!/usr/bin/env python3
"""
Touch Input Forwarder for Xvfb Display
Forwards touch events from physical touchscreen to virtual X display
"""
import evdev
import subprocess
import time
import sys

# Screen dimensions
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240

# Debounce settings
MIN_CLICK_INTERVAL = 0.05  # Minimum 50ms between clicks for faster response
last_click_time = 0

def find_touch_device():
    """Auto-detect the touchscreen device"""
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    
    for device in devices:
        name = device.name.lower()
        # Look for common touch device names
        if 'touch' in name or 'ili' in name or 'ft' in name or 'goodix' in name:
            print(f"Found touch device: {device.name} at {device.path}")
            return device
    
    print("No touch device found, checking all input devices:")
    for device in devices:
        caps = device.capabilities(verbose=True)
        print(f"  {device.name}: {device.path}")
        # Check if device has absolute positioning (typical for touchscreens)
        if ('EV_ABS', evdev.ecodes.EV_ABS) in caps:
            abs_info = caps[('EV_ABS', evdev.ecodes.EV_ABS)]
            # Check if it has X and Y axes
            has_x = any('ABS_X' in str(axis) or 'ABS_MT_POSITION_X' in str(axis) for axis, _ in abs_info)
            has_y = any('ABS_Y' in str(axis) or 'ABS_MT_POSITION_Y' in str(axis) for axis, _ in abs_info)
            if has_x and has_y:
                print(f"Using device with ABS positioning: {device.name}")
                return device
    
    return None

def get_touch_bounds(device):
    """Get the touch coordinate bounds from the device"""
    caps = device.capabilities(absinfo=True)
    
    # Try multitouch first
    if evdev.ecodes.EV_ABS in caps:
        abs_info = caps[evdev.ecodes.EV_ABS]
        
        # Check for multitouch
        if evdev.ecodes.ABS_MT_POSITION_X in abs_info:
            x_info = abs_info[evdev.ecodes.ABS_MT_POSITION_X]
            y_info = abs_info[evdev.ecodes.ABS_MT_POSITION_Y]
            return x_info.min, x_info.max, y_info.min, y_info.max
        
        # Check for single touch
        if evdev.ecodes.ABS_X in abs_info:
            x_info = abs_info[evdev.ecodes.ABS_X]
            y_info = abs_info[evdev.ecodes.ABS_Y]
            return x_info.min, x_info.max, y_info.min, y_info.max
    
    # Default bounds if we can't detect
    print("Warning: Could not detect touch bounds, using defaults (0-4095)")
    return 0, 4095, 0, 4095

def main():
    device = find_touch_device()
    if not device:
        print("ERROR: No touch device found!")
        sys.exit(1)
    
    # Get touch coordinate bounds
    x_min, x_max, y_min, y_max = get_touch_bounds(device)
    print(f"Touch bounds: X({x_min}-{x_max}) Y({y_min}-{y_max})")
    
    # Try to grab exclusive access
    try:
        device.grab()
        print("Grabbed exclusive access to touch device")
    except:
        print("Warning: Could not grab exclusive access")
    
    print(f"Forwarding touch events to X display :99 ({SCREEN_WIDTH}x{SCREEN_HEIGHT})")
    print("Touch forwarding active...")
    
    global last_click_time
    touching = False
    touch_down_pending = False
    x = 0
    y = 0
    x_raw = 0
    y_raw = 0
    
    try:
        for event in device.read_loop():
            # Capture position data
            if event.type == evdev.ecodes.EV_ABS:
                if event.code == evdev.ecodes.ABS_X:
                    x_raw = event.value
                    x = int((event.value - x_min) * SCREEN_WIDTH / (x_max - x_min))
                    x = max(0, min(SCREEN_WIDTH - 1, x))
                    
                elif event.code == evdev.ecodes.ABS_Y:
                    y_raw = event.value
                    # Invert Y axis - touchscreen is flipped
                    y = SCREEN_HEIGHT - int((event.value - y_min) * SCREEN_HEIGHT / (y_max - y_min))
                    y = max(0, min(SCREEN_HEIGHT - 1, y))
            
            # Capture touch button state
            elif event.type == evdev.ecodes.EV_KEY:
                if event.code == evdev.ecodes.BTN_TOUCH:
                    if event.value == 1:  # Touch down
                        touching = True
                        touch_down_pending = True
                    elif event.value == 0:  # Touch up
                        touching = False
                        try:
                            subprocess.run(
                                ['xdotool', 'mouseup', '1'],
                                env={'DISPLAY': ':99'},
                                check=False,
                                capture_output=True
                            )
                        except Exception as e:
                            print(f"Release error: {e}")
            
            # Wait for SYN event (marks end of event packet) before acting
            elif event.type == evdev.ecodes.EV_SYN and event.code == evdev.ecodes.SYN_REPORT:
                if touch_down_pending:
                    touch_down_pending = False
                    current_time = time.time()
                    
                    if current_time - last_click_time >= MIN_CLICK_INTERVAL:
                        try:
                            print(f"Touch at: ({x}, {y}) [raw: {x_raw}, {y_raw}]")
                            subprocess.run(
                                ['xdotool', 'mousemove', '--sync', str(x), str(y), 'mousedown', '1'],
                                env={'DISPLAY': ':99'},
                                check=False,
                                capture_output=True
                            )
                            last_click_time = current_time
                        except Exception as e:
                            print(f"Click error: {e}")
    
    except KeyboardInterrupt:
        print("\nTouch forwarding stopped")
    finally:
        try:
            device.ungrab()
        except:
            pass

if __name__ == '__main__':
    main()
