# USB Battery Device Maintainer

> ⚠️ **ALPHA SOFTWARE** - This project is in early development and testing. Not recommended for production use.

A smart battery maintenance system for Raspberry Pi with Argon POD display support. Automatically maintains USB-powered devices through intelligent charging cycles to optimize battery health and longevity.

## Features

- 🔋 **Intelligent Charging Cycles** - Automatically charges devices on a configurable schedule
- 📊 **Real-time Monitoring** - Track battery voltage and port status
- 🎮 **Touch Interface** - 320x240 touchscreen UI optimized for Argon POD
- ⚙️ **Configurable Settings** - Adjust USB ports, charge duration, cycle days, and brightness
- 🔌 **USB Port Control** - Turn individual USB ports on/off via uhubctl
- 📈 **INA219 Sensor Support** - Monitor current and voltage per port
- 🚀 **Auto-start Service** - Runs automatically on boot

## Hardware Requirements

- Raspberry Pi (3/4/5 or Zero 2 W)
- Argon POD case with display (or any 320x240 touchscreen)
- USB hub with per-port power control (uhubctl compatible)
- (Optional) INA219 current/voltage sensors for monitoring
- (Optional) ADS1115 ADC for battery voltage reading

## Quick Start

### Installation

1. **Install Git (if not already installed):**
   ```bash
   sudo apt update && sudo apt install -y git
   ```

2. **Download and transfer to Raspberry Pi:**
   ```bash
   git clone https://github.com/collingerac/USB-Battery-Device-Maintainer.git
   cd USB-Battery-Device-Maintainer
   ```

3. **Run the installer:**
   ```bash
   chmod +x battery_maintainer_installer.sh
   ./battery_maintainer_installer.sh
   ```

4. **Reboot:**
   ```bash
   sudo reboot
   ```

The application will start automatically on boot!

### Manual Installation

See [ARGON_POD_SETUP.md](ARGON_POD_SETUP.md) for detailed setup instructions.

## Configuration

Edit `/home/pi/battery_maintainer/config.json`:

```json
{
  "BUS": 1,
  "PORT": 2,
  "CHARGE_MINUTES": 45,
  "CYCLE_DAYS": 150,
  "BRIGHTNESS": 50
}
```

Or use the built-in Settings screen on the touchscreen interface.

## Usage

### Touch Interface

- **Main Screen:** View battery status and next charge time
- **Force Charge:** Tap "FORCE CHARGE NOW" for manual charging
- **Settings:** Configure USB ports, charge duration, and brightness

### Command Line

```bash
# Check status
sudo systemctl status battery-maintainer

# Start/stop/restart
sudo systemctl start battery-maintainer
sudo systemctl stop battery-maintainer
sudo systemctl restart battery-maintainer

# View logs
journalctl -u battery-maintainer -f
```

## Project Structure

```
battery-charging-manager/
├── battery_maintainer.py          # Main application
├── battery_maintainer_installer.sh # Automated installer
├── battery-maintainer.service      # Systemd service file
├── gui_installer.py                # GUI installer (for desktop)
├── make_executable.py              # Helper to make scripts executable
├── config.json                     # Configuration template
├── fonts/
│   └── boxicons.ttf               # Icon font
├── ARGON_POD_SETUP.md             # Detailed setup guide
└── README.md                       # This file
```

## Screenshots

*(Add screenshots of your UI here)*

## Troubleshooting

### Display Not Working
```bash
argonpod-config --enable-display --display_rotate=2
sudo reboot
```

### I2C Sensors Not Detected
```bash
sudo i2cdetect -y 1
```

### USB Control Not Working
```bash
sudo uhubctl  # List controllable hubs
```

See [ARGON_POD_SETUP.md](ARGON_POD_SETUP.md) for more troubleshooting steps.

## Development

### Running on Windows (for UI development)
```bash
python battery_maintainer.py
```

Hardware features will be disabled, but the UI will work for testing.

### Dependencies

- Python 3.7+
- Kivy
- adafruit-circuitpython-ina219
- adafruit-circuitpython-ads1x15
- adafruit-blinka
- uhubctl

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## License

MIT License - See LICENSE file for details

## Support

For issues and questions, please open an issue on GitHub.

## Credits

- Built with [Kivy](https://kivy.org/)
- Icons from [Boxicons](https://boxicons.com/)
- Designed for [Argon POD](https://www.argon40.com/)

## Version

Current version: **0.1.1-alpha**

⚠️ **Alpha Release** - This software is in early testing. Features may be incomplete or unstable. Use at your own risk and report any issues on GitHub.

## Release Notes

### 0.1.1-alpha (2025-12-10)
- Added network settings to the Settings tab:
   - IP address input field
   - Static IP toggle (best-effort application for Debian using /etc/dhcpcd.conf)
   - SSH enable/disable toggle (attempts to enable/disable `ssh` service)

- Added a touchscreen-friendly on-screen keyboard used in the Settings screen

Notes: Static IP application is best-effort and requires root to write `/etc/dhcpcd.conf` and restart `dhcpcd`. The app will persist the settings to the config file even if automatic application fails; check logs for errors.


### Known Limitations
- [ ] Limited hardware testing
- [ ] I2C sensor support needs validation
- [ ] USB hub compatibility varies
- [ ] Brightness control only tested on Argon POD

### Roadmap to Stable Release
- [ ] Test on multiple Raspberry Pi models
- [ ] Validate sensor readings
- [ ] Add error recovery mechanisms  
- [ ] Comprehensive documentation
- [ ] Community testing feedback

