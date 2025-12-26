#!/bin/bash
# Battery Maintainer Installer 
# version 0.1.3-alpha
# Status: Alpha - Testing Phase

# Updating system packages
sudo apt update && sudo apt upgrade -y

# Remove conflicting packages if they exist
echo "Removing any conflicting packages..."
sudo apt remove -y python3-kivy python3-kivy-examples 2>/dev/null || true

# Install required packages
sudo apt install wget -y
sudo apt install unzip -y
sudo apt install cmake git -y
sudo apt install python3-pip python3-setuptools python3-dev -y
sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev -y
sudo apt install pkg-config libgl1-mesa-dev libgles2-mesa-dev -y
sudo apt install libmtdev-dev -y
sudo apt install uhubctl -y
sudo apt install python3-usb -y

# Install Xvfb for virtual display and ffmpeg for framebuffer mirroring
echo "Installing virtual display system..."
sudo apt install -y xvfb ffmpeg unclutter xdotool python3-evdev

# Install Python packages via pip (without X11 dependencies)
echo "Installing Python packages..."
sudo pip3 install Cython==0.29.36 --break-system-packages --root-user-action=ignore
sudo pip3 install kivy[base] --break-system-packages --root-user-action=ignore
sudo pip3 install adafruit-circuitpython-ads1x15 --break-system-packages --root-user-action=ignore
sudo pip3 install adafruit-circuitpython-busdevice --break-system-packages --root-user-action=ignore
sudo pip3 install adafruit-blinka --break-system-packages --root-user-action=ignore
sudo pip3 install adafruit-circuitpython-ina219 --break-system-packages --root-user-action=ignore
sudo pip3 install kivy-garden --break-system-packages --root-user-action=ignore

# Add pi user to video group for framebuffer access
echo "Adding pi user to video group..."
sudo usermod -a -G video pi

# Enable I2C
sudo raspi-config nonint do_i2c 0

# Verify I2C was enabled successfully
echo "Verifying I2C configuration..."
I2C_STATUS=$(sudo raspi-config nonint get_i2c)
if [ "$I2C_STATUS" -eq 0 ]; then
    echo "✓ I2C enabled successfully"
else
    echo "✗ Warning: I2C may not be enabled. Status: $I2C_STATUS"
fi


# Download and install Boxicons font if not present
echo "Checking for Boxicons font..."
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
FONTS_DIR="$SCRIPT_DIR/fonts"
BOXICONS_TTF="$FONTS_DIR/boxicons.ttf"
BOXICONS_CSS="$FONTS_DIR/boxicons.css"

# Pin to specific version to prevent future releases from breaking icon codes
BOXICONS_VERSION="2.1.4"

if [ -f "$BOXICONS_TTF" ] && [ -f "$BOXICONS_CSS" ]; then
    echo "✓ Boxicons font and CSS already exist"
else
    echo "Downloading Boxicons font and CSS (version ${BOXICONS_VERSION})..."
    mkdir -p "$FONTS_DIR"
    
    # Download TTF font from pinned version
    echo "Downloading boxicons.ttf (v${BOXICONS_VERSION})..."
    wget -q "https://cdn.jsdelivr.net/npm/boxicons@${BOXICONS_VERSION}/fonts/boxicons.ttf" -O "$BOXICONS_TTF"
    
    if [ $? -eq 0 ] && [ -f "$BOXICONS_TTF" ] && [ -s "$BOXICONS_TTF" ]; then
        echo "✓ Boxicons TTF v${BOXICONS_VERSION} downloaded successfully"
    else
        echo "✗ Warning: Failed to download boxicons.ttf v${BOXICONS_VERSION}"
        rm -f "$BOXICONS_TTF"
    fi
    
    # Download CSS file for icon mappings from pinned version
    echo "Downloading boxicons.css (v${BOXICONS_VERSION})..."
    wget -q "https://cdn.jsdelivr.net/npm/boxicons@${BOXICONS_VERSION}/css/boxicons.css" -O "$BOXICONS_CSS"
    
    if [ $? -eq 0 ] && [ -f "$BOXICONS_CSS" ] && [ -s "$BOXICONS_CSS" ]; then
        echo "✓ Boxicons CSS v${BOXICONS_VERSION} downloaded successfully"
    else
        echo "✗ Warning: Failed to download boxicons.css v${BOXICONS_VERSION}"
        rm -f "$BOXICONS_CSS"
    fi
fi



# NOTE: Only install Argon POD Drivers if installing on Argon devices
# Prompt user to confirm if they're using an Argon device
read -p "Are you installing on an Argon POD device? (y/n): " -n 1 -r
echo
ARGON_INSTALLED=false
if [[ $REPLY =~ ^[Yy]$ ]]; then
	echo "Installing Argon POD system drivers..."
	curl -sSL https://download.argon40.com/podsystem.sh | sudo bash
	# Configuring Argon POD system
	if command -v argonpod-config &> /dev/null; then
		echo "Configuring Argon POD display..."
		sudo argonpod-config --enable-touch --enable-display --display_rotate=3 --non-interactive 2>/dev/null || \
		sudo argonpod-config --enable-touch --enable-display --display_rotate=3 < /dev/null
		# Enable Argon POD to start on boot (only if service exists)
		sudo systemctl daemon-reload
		if sudo systemctl enable argonpod 2>/dev/null; then
			echo "Argon POD service enabled for auto-start"
		else
			echo "Note: argonpod service not available - display will be configured via kernel modules"
		fi
           ARGON_INSTALLED=true
           echo "Argon POD drivers installed and configured successfully."
           echo "Note: Display rotation will take effect after reboot."

           # Configure X server for fb1 framebuffer and disable HDMI/cursor ONLY for Argon POD
           echo ""
           echo "Configuring system for Argon POD display..."

           # Disable HDMI to make Argon POD (fb1) the primary display
           if ! grep -q "hdmi_blanking=2" /boot/firmware/config.txt; then
               echo "Disabling HDMI output..."
               sudo bash -c 'echo "" >> /boot/firmware/config.txt'
               sudo bash -c 'echo "# Disable HDMI for Argon POD primary display" >> /boot/firmware/config.txt'
               sudo bash -c 'echo "hdmi_blanking=2" >> /boot/firmware/config.txt'
               sudo bash -c 'echo "disable_splash=1" >> /boot/firmware/config.txt'
           fi

           # Disable console cursor
           if ! grep -q "vt.global_cursor_default=0" /boot/firmware/cmdline.txt; then
               echo "Disabling console cursor..."
               sudo sed -i 's/$/ vt.global_cursor_default=0/' /boot/firmware/cmdline.txt
           fi

           echo "✓ System configured for Argon POD display"
	else
		echo "Warning: Argon POD configuration command not found after installation."
	fi
else
    echo "Skipping Argon POD driver installation."
fi


# Copy application files to /home/pi
echo ""
echo "Installing application files..."
INSTALL_DIR="/home/pi/battery_maintainer"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/fonts"

# Copy files
cp "$SCRIPT_DIR/battery_maintainer.py" "$INSTALL_DIR/" 2>/dev/null || echo "Warning: Could not copy battery_maintainer.py"

# Create default config.json if it doesn't exist in source or destination
if [ ! -f "$SCRIPT_DIR/config.json" ]; then
    echo "Creating default config.json..."
    cat > "$INSTALL_DIR/config.json" << 'CONFIGEOF'
{
  "BUS": 1,
  "PORT": 0,
  "CHARGE_MINUTES": 45,
  "CYCLE_DAYS": 150,
  "BRIGHTNESS": 50,
  "IP_ADDRESS": "192.168.1.100",
  "SSH_ENABLED": false,
  "STATIC_IP": false
}
CONFIGEOF
else
    cp "$SCRIPT_DIR/config.json" "$INSTALL_DIR/" 2>/dev/null
fi

cp -r "$SCRIPT_DIR/fonts/"* "$INSTALL_DIR/fonts/" 2>/dev/null || echo "Warning: Could not copy fonts"

# Set permissions
chown -R pi:pi "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/battery_maintainer.py"

echo "✓ Application files installed to $INSTALL_DIR"

echo "✓ System configured for Argon POD display"

# Install touch forwarding script
echo ""
echo "Installing touch input forwarding script..."
if [ -f "$SCRIPT_DIR/touch-to-xvfb.py" ]; then
    # Copy to project folder
    cp "$SCRIPT_DIR/touch-to-xvfb.py" "$INSTALL_DIR/touch-to-xvfb.py"
    chmod +x "$INSTALL_DIR/touch-to-xvfb.py"
    chown pi:pi "$INSTALL_DIR/touch-to-xvfb.py"
    
    # Create symlink in /usr/local/bin for system-wide access
    sudo ln -sf "$INSTALL_DIR/touch-to-xvfb.py" /usr/local/bin/touch-to-xvfb.py
    echo "✓ Touch forwarding script installed"
    echo "  Location: $INSTALL_DIR/touch-to-xvfb.py"
    echo "  Symlinked to: /usr/local/bin/touch-to-xvfb.py"
else
    echo "✗ Warning: touch-to-xvfb.py not found in $SCRIPT_DIR"
    echo "  Touch input may not work. Please ensure touch-to-xvfb.py is in the same directory as the installer."
fi

# Create startup script
echo ""
echo "Creating startup script..."
sudo tee /usr/local/bin/battery-maintainer-start.sh > /dev/null << 'STARTSCRIPT'
#!/bin/bash
# Start Xvfb virtual display
Xvfb :99 -screen 0 320x240x24 &
XVFB_PID=$!
sleep 3

# Hide the X cursor
export DISPLAY=:99
unclutter -idle 0 -root &

# Start touch input forwarder
python3 /usr/local/bin/touch-to-xvfb.py &
TOUCH_PID=$!

# Start the Python app
cd /home/pi/battery_maintainer
python3 battery_maintainer.py &
APP_PID=$!
sleep 5

# Start ffmpeg to mirror to Argon POD
ffmpeg -loglevel error -f x11grab -video_size 320x240 -framerate 10 -i :99 -pix_fmt rgb565le -f fbdev /dev/fb1 &
FFMPEG_PID=$!

# Wait for any process to exit
wait
STARTSCRIPT

sudo chmod +x /usr/local/bin/battery-maintainer-start.sh
echo "✓ Startup script created"

# Install systemd service for auto-start
echo ""
echo "Setting up auto-start service..."
SERVICE_FILE="/etc/systemd/system/battery-maintainer.service"

sudo tee "$SERVICE_FILE" > /dev/null << 'SERVICEEOF'
[Unit]
Description=Battery Maintainer Application
After=graphical.target argonpod.service
Wants=graphical.target

[Service]
Type=simple
User=pi
# Remove DISPLAY for framebuffer (Argon POD)
Environment=KIVY_WINDOW=sdl2
WorkingDirectory=/home/pi/USB-Battery-Device-Maintainer
ExecStart=/usr/bin/python3 /home/pi/USB-Battery-Device-Maintainer/battery_maintainer.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
SERVICEEOF

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable battery-maintainer.service

echo "✓ Auto-start service installed"
echo ""
echo "Testing service configuration..."
# Try to start the service immediately to check for errors
if sudo systemctl start battery-maintainer.service; then
    sleep 3
    if sudo systemctl is-active --quiet battery-maintainer.service; then
        echo "✓ Service started successfully"
    else
        echo "✗ Service failed to start - checking logs..."
        sudo journalctl -u battery-maintainer -n 20 --no-pager
    fi
else
    echo "✗ Service failed to start - checking logs..."
    sudo journalctl -u battery-maintainer -n 20 --no-pager
fi

echo ""
echo "======================================================================"
echo "Installation Complete!"
echo "======================================================================"
echo ""
echo "Next steps:"
echo "1. Check service status: sudo systemctl status battery-maintainer"
echo "2. View logs: sudo journalctl -u battery-maintainer -f"
echo "3. Edit config if needed: nano /home/pi/battery_maintainer/config.json"
echo "4. Reboot the system: sudo reboot"
echo ""
echo "If the service isn't running, check:"
echo "  - Framebuffer device exists: ls -l /dev/fb*"
echo "  - Python dependencies: pip3 list | grep kivy"
echo "  - Application file exists: ls -l /home/pi/battery_maintainer/"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status battery-maintainer   # Check app status"
echo "  sudo systemctl restart battery-maintainer  # Restart app"
echo "  sudo systemctl stop battery-maintainer     # Stop app"
echo "  sudo systemctl disable battery-maintainer  # Disable auto-start"
echo "  sudo journalctl -u battery-maintainer -f   # View live logs"
echo ""

