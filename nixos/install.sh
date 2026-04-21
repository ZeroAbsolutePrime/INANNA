#!/usr/bin/env bash
set -euo pipefail

echo "INANNA NYX - Installation Script"
echo ""

if [ ! -f /etc/nixos/configuration.nix ]; then
  echo "Error: /etc/nixos/configuration.nix not found."
  echo "This script is for NixOS only."
  exit 1
fi

INANNA_HOME="/home/inanna/INANNA"

echo "Installing NixOS configuration..."
sudo cp "$(dirname "$0")/configuration.nix" /etc/nixos/configuration.nix

echo "Rebuilding NixOS..."
sudo nixos-rebuild switch

if [ ! -d "$INANNA_HOME" ]; then
  echo "Cloning INANNA NYX repository..."
  sudo -u inanna git clone https://github.com/ZeroAbsolutePrime/INANNA "$INANNA_HOME"
fi

echo "Installing Python dependencies..."
cd "$INANNA_HOME/inanna"
sudo -u inanna python3 -m pip install --user -r requirements.txt

echo "Restarting INANNA NYX service..."
sudo systemctl restart inanna-nyx

echo ""
echo "INANNA NYX installed."
echo "Service status: systemctl status inanna-nyx"
echo "Logs: journalctl -u inanna-nyx -f"
echo "Access at: http://localhost:8080"
