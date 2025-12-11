#!/bin/bash
# Battery Maintainer Installer 
# version 0.1.1-alpha
# Status: Alpha - Testing Phase

# Updating system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install wget -y
sudo apt install unzip -y
sudo apt install cmake git -y
sudo apt install pipx -y
sudo apt install python3-pip python3-setuptools python3-dev -y
sudo apt-get install python3-kivy -y
sudo apt install uhubctl -y
sudo apt install python3-usb -y
sudo pip3 install adafruit-circuitpython-ads1x15 --break-system-packages
sudo pip3 install adafruit-circuitpython-busdevice --break-system-packages
sudo pip3 install adafruit-blinka --break-system-packages
sudo pip3 install adafruit-circuitpython-ina219 --break-system-packages
# Install Kivy Garden (iconfonts is optional - app will work without it)
sudo pip3 install kivy-garden --break-system-packages
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

if [ -f "$BOXICONS_TTF" ]; then
    echo "✓ Boxicons font already exists"
else
    echo "Downloading Boxicons font..."
    mkdir -p "$FONTS_DIR"
    
    # Fetch the latest Boxicons release version from GitHub API
    echo "Fetching latest Boxicons version..."
    BOXICONS_VERSION=$(curl -s https://api.github.com/repos/atisawd/boxicons/releases/latest | grep '"tag_name":' | sed -E 's/.*"v([^"]+)".*/\1/')
    
    if [ -z "$BOXICONS_VERSION" ]; then
        echo "Could not fetch latest version, using v2.1.4 as fallback"
        BOXICONS_VERSION="2.1.4"
    else
        echo "Latest version: v$BOXICONS_VERSION"
    fi
    
    # Download Boxicons release
    wget -q "https://github.com/atisawd/boxicons/archive/v${BOXICONS_VERSION}.zip" -O /tmp/boxicons.zip
    
    if [ $? -eq 0 ]; then
        echo "Download complete, extracting font file..."
        # Extract the font file
        unzip -q -j /tmp/boxicons.zip "boxicons-${BOXICONS_VERSION}/fonts/boxicons.ttf" -d "$FONTS_DIR" 2>/dev/null
        
        if [ $? -ne 0 ]; then
            # Try alternative extraction path (in case folder structure is different)
            unzip -q /tmp/boxicons.zip "*/fonts/boxicons.ttf" 2>/dev/null
            find /tmp -name "boxicons.ttf" -exec cp {} "$FONTS_DIR/" \; 2>/dev/null
        fi
        
        rm /tmp/boxicons.zip
        
        if [ -f "$BOXICONS_TTF" ]; then
            echo "✓ Boxicons font v$BOXICONS_VERSION downloaded successfully"
        else
            echo "✗ Warning: Failed to extract Boxicons font"
            echo "  You can manually download from: https://boxicons.com/"
        fi
    else
        echo "✗ Warning: Failed to download Boxicons. App will work without icons."
    fi
fi



# NOTE: Only install Argon POD Drivers if installing on Argon devices
# Prompt user to confirm if they're using an Argon device
read -p "Are you installing on an Argon POD device? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
	echo "Installing Argon POD system drivers..."
	curl -sSL https://download.argon40.com/podsystem.sh | sudo bash
	# Configuring Argon POD system
	if command -v argonpod-config &> /dev/null; then
		argonpod-config --enable-touch --enable-display --display_rotate=2
		# Enable Argon POD to start on boot
		sudo systemctl enable argonpod
		echo "Argon POD drivers installed and configured successfully."
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
cp "$SCRIPT_DIR/config.json" "$INSTALL_DIR/" 2>/dev/null || echo "Config file not found, will be created on first run"
cp -r "$SCRIPT_DIR/fonts/"* "$INSTALL_DIR/fonts/" 2>/dev/null || echo "Warning: Could not copy fonts"

# Set permissions
chown -R pi:pi "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/battery_maintainer.py"

echo "✓ Application files installed to $INSTALL_DIR"

# Install systemd service for auto-start
echo ""
echo "Setting up auto-start service..."
SERVICE_FILE="/etc/systemd/system/battery-maintainer.service"

cat > "$SERVICE_FILE" << 'SERVICEEOF'
[Unit]
Description=Battery Maintainer Application
After=graphical.target argonpod.service
Wants=graphical.target

[Service]
Type=simple
User=pi
Environment=DISPLAY=:0
Environment=KIVY_WINDOW=sdl2
WorkingDirectory=/home/pi/battery_maintainer
ExecStart=/usr/bin/python3 /home/pi/battery_maintainer/battery_maintainer.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=graphical.target
SERVICEEOF

# Reload systemd and enable service
systemctl daemon-reload
systemctl enable battery-maintainer.service

echo "✓ Auto-start service installed"
echo ""
echo "=" * 70
echo "Installation Complete!"
echo "=" * 70
echo ""
echo "Next steps:"
echo "1. Edit /home/pi/battery_maintainer/config.json to configure USB ports"
echo "2. Reboot the system: sudo reboot"
echo "3. The app will start automatically on boot"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status battery-maintainer   # Check app status"
echo "  sudo systemctl restart battery-maintainer  # Restart app"
echo "  sudo systemctl stop battery-maintainer     # Stop app"
echo "  sudo systemctl disable battery-maintainer  # Disable auto-start"
echo ""

