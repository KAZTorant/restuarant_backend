#!/bin/bash

# Quick Start Script for WhatsApp Integration
# This script helps you set up the WhatsApp Web service quickly

set -e

echo "============================================================"
echo "🚀 WhatsApp Integration Quick Start"
echo "============================================================"

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo ""
    echo "❌ Node.js is not installed!"
    echo ""
    echo "Please install Node.js first:"
    echo "  macOS: brew install node"
    echo "  Ubuntu: sudo apt install nodejs npm"
    echo "  Or download from: https://nodejs.org/"
    exit 1
fi

echo ""
echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Navigate to whatsapp_service directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WHATSAPP_DIR="$SCRIPT_DIR/whatsapp_service"

echo ""
echo "📂 WhatsApp service directory: $WHATSAPP_DIR"

if [ ! -d "$WHATSAPP_DIR" ]; then
    echo "❌ WhatsApp service directory not found!"
    exit 1
fi

cd "$WHATSAPP_DIR"

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo ""
    echo "📦 Installing dependencies..."
    npm install
    echo "✅ Dependencies installed"
else
    echo ""
    echo "✅ Dependencies already installed"
fi

# Check .env configuration
ENV_FILE="$SCRIPT_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
    echo ""
    echo "⚠️  .env file not found"
    echo "Creating .env file with default configuration..."
    
    cat > "$ENV_FILE" << EOF
# WhatsApp Configuration
WHATSAPP_SERVICE_URL=http://localhost:3001
RESTAURANT_OWNER_PHONE=

# Add your restaurant owner's phone number above (format: 501234567)
EOF
    
    echo "✅ Created .env file at: $ENV_FILE"
    echo ""
    echo "⚠️  IMPORTANT: Please edit .env and add RESTAURANT_OWNER_PHONE"
fi

# Display configuration status
echo ""
echo "============================================================"
echo "📋 Configuration Status"
echo "============================================================"

if [ -f "$ENV_FILE" ]; then
    source "$ENV_FILE"
    
    if [ -z "$RESTAURANT_OWNER_PHONE" ]; then
        echo "⚠️  Owner phone: NOT CONFIGURED"
        echo "   Please edit .env and set RESTAURANT_OWNER_PHONE=501234567"
    else
        echo "✅ Owner phone: $RESTAURANT_OWNER_PHONE"
    fi
    
    echo "✅ Service URL: ${WHATSAPP_SERVICE_URL:-http://localhost:3001}"
else
    echo "⚠️  Configuration file not found"
fi

echo ""
echo "============================================================"
echo "🎯 Next Steps"
echo "============================================================"
echo ""
echo "1️⃣  Configure owner phone number (if not done):"
echo "   Edit .env and set: RESTAURANT_OWNER_PHONE=501234567"
echo ""
echo "2️⃣  Start WhatsApp service:"
echo "   cd whatsapp_service && npm start"
echo ""
echo "3️⃣  Scan QR code with restaurant phone:"
echo "   - Open WhatsApp"
echo "   - Go to Settings → Linked Devices"
echo "   - Scan QR code from terminal"
echo ""
echo "4️⃣  Test the integration:"
echo "   python test_whatsapp_integration.py"
echo ""
echo "============================================================"
echo ""

# Ask if user wants to start the service now
read -p "Do you want to start the WhatsApp service now? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🚀 Starting WhatsApp service..."
    echo ""
    echo "============================================================"
    echo "📱 SCAN THE QR CODE THAT APPEARS BELOW"
    echo "============================================================"
    echo ""
    npm start
else
    echo ""
    echo "👍 Okay! Start the service later with:"
    echo "   cd whatsapp_service && npm start"
    echo ""
fi
