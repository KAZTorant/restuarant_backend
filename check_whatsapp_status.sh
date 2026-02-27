#!/bin/bash

# WhatsApp Service Status Checker
# Quick script to check if WhatsApp service is running and configured

SERVICE_URL="${WHATSAPP_SERVICE_URL:-http://localhost:3001}"

echo "============================================================"
echo "📊 WhatsApp Service Status"
echo "============================================================"
echo ""

# Check if service is reachable
echo "🔍 Checking service at: $SERVICE_URL"
echo ""

if ! command -v curl &> /dev/null; then
    echo "❌ curl is not installed. Please install curl first."
    exit 1
fi

# Health check
echo "1️⃣  Service Health:"
HEALTH=$(curl -s -w "\n%{http_code}" "$SERVICE_URL/health" 2>/dev/null)
HTTP_CODE=$(echo "$HEALTH" | tail -n1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "   ✅ Service is running"
    HEALTH_DATA=$(echo "$HEALTH" | head -n1)
    echo "   $HEALTH_DATA" | python3 -m json.tool 2>/dev/null || echo "   $HEALTH_DATA"
else
    echo "   ❌ Service is not running or not reachable"
    echo "   HTTP Code: $HTTP_CODE"
    echo ""
    echo "   To start the service:"
    echo "   cd whatsapp_service && npm start"
    exit 1
fi

echo ""

# Status check
echo "2️⃣  WhatsApp Connection:"
STATUS=$(curl -s "$SERVICE_URL/status" 2>/dev/null)

if [ -n "$STATUS" ]; then
    READY=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('ready', False))" 2>/dev/null)
    MESSAGE=$(echo "$STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('message', 'Unknown'))" 2>/dev/null)
    
    if [ "$READY" = "True" ]; then
        echo "   ✅ WhatsApp is connected and ready"
        echo "   Message: $MESSAGE"
    else
        echo "   ⚠️  WhatsApp is NOT ready"
        echo "   Message: $MESSAGE"
        echo ""
        echo "   To authenticate:"
        echo "   1. Look for QR code in the service terminal"
        echo "   2. Open WhatsApp → Settings → Linked Devices"
        echo "   3. Scan the QR code"
    fi
else
    echo "   ❌ Could not get status"
fi

echo ""

# Configuration check
echo "3️⃣  Configuration:"
if [ -f ".env" ]; then
    source .env
    if [ -n "$RESTAURANT_OWNER_PHONE" ]; then
        echo "   ✅ Owner phone: $RESTAURANT_OWNER_PHONE"
    else
        echo "   ⚠️  Owner phone not configured"
        echo "   Edit .env and set: RESTAURANT_OWNER_PHONE=501234567"
    fi
    echo "   ✅ Service URL: ${WHATSAPP_SERVICE_URL:-http://localhost:3001}"
else
    echo "   ⚠️  .env file not found"
    echo "   Run: ./setup_whatsapp.sh"
fi

echo ""
echo "============================================================"
echo ""

# Summary
if [ "$HTTP_CODE" = "200" ] && [ "$READY" = "True" ] && [ -n "$RESTAURANT_OWNER_PHONE" ]; then
    echo "🎉 Everything is configured and working!"
    echo ""
    echo "To test, run: python test_whatsapp_integration.py"
else
    echo "⚠️  Action required - see messages above"
fi

echo ""
