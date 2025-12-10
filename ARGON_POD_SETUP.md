# USB Battery Device Maintainer - Argon POD Setup Guide

## Overview
This guide helps you install and run the USB Battery Device Maintainer on a headless Raspberry Pi with an Argon POD display (320x240 touchscreen).

## Prerequisites
- Raspberry Pi Zero 2 W
- Argon POD case with display 
- SSH access to the Raspberry Pi
- Internet connection

## Installation Steps

### 1. Transfer Files to Raspberry Pi

Copy all project files to your Raspberry Pi:

```bash
# From your computer, use SCP
scp -r "USB Device Battery Charging Manager" pi@raspberrypi.local:~/battery_maintainer_setup

# Or use rsync for better handling
rsync -avz --progress "USB Device Battery Charging Manager/" pi@raspberrypi.local:~/battery_maintainer_setup/
```

### 2. SSH into Raspberry Pi

```bash
ssh pi@raspberrypi.local
```

### 3. Run the Installer

```bash
cd ~/battery_maintainer_setup
chmod +x battery_maintainer_installer.sh
./battery_maintainer_installer.sh
```

When prompted:
- Answer **Y** for "Install Argon POD drivers"
- Wait for installation to complete (10-20 minutes)

### 4. Configure the Application

Edit the config file:

```bash
nano /home/pi/battery_maintainer/config.json
```

Set your USB bus and port:

```json
{
  "BUS": 1,
  "PORT": 2
}
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

### 5. Reboot

```bash
sudo reboot
```

## Verification

After reboot, the app should start automatically on the Argon POD display.

### Check if App is Running

```bash
sudo systemctl status battery-maintainer
```

You should see `active (running)` in green.

### View Logs

```bash
journalctl -u battery-maintainer -f
```

Press `Ctrl+C` to exit.

## Troubleshooting

### Display Not Working

1. **Verify Argon POD is installed:**
   ```bash
   systemctl status argonpod
   ```

2. **Check display rotation:**
   ```bash
   argonpod-config --display_rotate=2
   sudo reboot
   ```

3. **Test display manually:**
   ```bash
   DISPLAY=:0 python3 /home/pi/battery_maintainer/battery_maintainer.py
   ```

### App Not Starting

1. **Check for errors:**
   ```bash
   journalctl -u battery-maintainer -n 50
   ```

2. **Test manually:**
   ```bash
   cd /home/pi/battery_maintainer
   python3 battery_maintainer.py
   ```

3. **Check Python dependencies:**
   ```bash
   pip3 list | grep -E "kivy|adafruit"
   ```

### I2C Sensors Not Working

1. **Verify I2C is enabled:**
   ```bash
   ls /dev/i2c*
   ```
   Should show `/dev/i2c-1`

2. **Scan for devices:**
   ```bash
   sudo i2cdetect -y 1
   ```
   Should show addresses: 40, 41, 44, 45 for INA219 sensors

3. **Re-enable I2C:**
   ```bash
   sudo raspi-config nonint do_i2c 0
   sudo reboot
   ```

### USB Hub Control Not Working

1. **Test uhubctl manually:**
   ```bash
   sudo uhubctl
   ```

2. **Find your USB hub:**
   Look for controllable hub in output

3. **Test port control:**
   ```bash
   sudo uhubctl -l 1-1 -p 2 -a off
   sudo uhubctl -l 1-1 -p 2 -a on
   ```

## Manual Control Commands

### Start/Stop the App

```bash
sudo systemctl start battery-maintainer   # Start
sudo systemctl stop battery-maintainer    # Stop
sudo systemctl restart battery-maintainer # Restart
```

### Enable/Disable Auto-start

```bash
sudo systemctl enable battery-maintainer  # Auto-start on boot
sudo systemctl disable battery-maintainer # Don't auto-start
```

### Update the App

```bash
# Copy new battery_maintainer.py file
scp battery_maintainer.py pi@raspberrypi.local:/home/pi/battery_maintainer/

# Restart the service
ssh pi@raspberrypi.local
sudo systemctl restart battery-maintainer
```

## Argon POD Specific Settings

### Display Brightness

```bash
argonpod-config --brightness 50  # 0-100
```

### Touch Calibration

```bash
argonpod-config --enable-touch
```

### Display Rotation

```bash
# 0 = normal, 1 = 90°, 2 = 180°, 3 = 270°
argonpod-config --display_rotate=2
sudo reboot
```

## Performance Optimization for Headless

The app is configured for low resource usage:
- **10 FPS** limit to reduce CPU usage
- **30-second update interval** for battery readings
- **Software rendering** optimized for small display

## Remote Access

### VNC (Optional)
If you want to see the display remotely:

```bash
sudo raspi-config
# Interface Options → VNC → Enable
```

Then connect with VNC Viewer to `raspberrypi.local`

### Web Dashboard (Future Enhancement)
Consider adding a web interface for remote monitoring without VNC.

## Uninstall

```bash
# Stop and disable service
sudo systemctl stop battery-maintainer
sudo systemctl disable battery-maintainer

# Remove files
sudo rm /etc/systemd/system/battery-maintainer.service
rm -rf /home/pi/battery_maintainer

# Reload systemd
sudo systemctl daemon-reload
```

## Support

For issues or questions:
1. Check logs: `journalctl -u battery-maintainer`
2. Test sensors: `sudo i2cdetect -y 1`
3. Verify display: `DISPLAY=:0 xrandr`


