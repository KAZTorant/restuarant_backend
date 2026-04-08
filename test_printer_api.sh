#!/bin/bash

# Printer Module API Test Script
# Bu script printer modulunun bütün API endpoint-lərini test edir

BASE_URL="http://127.0.0.1:8000/api/printers"

# Rənglər
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "======================================"
echo "   PRINTER MODULE API TEST"
echo "======================================"
echo ""

# Token əldə et (admin user ilə)
echo -e "${YELLOW}1. Token əldə edilir...${NC}"
TOKEN_RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/api/users/login/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "devUser",
    "password": "1"
  }')

TOKEN=$(echo $TOKEN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ Token əldə edilə bilmədi!${NC}"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✓ Token əldə edildi${NC}"
echo ""

# Test 1: Printer List
echo -e "${YELLOW}2. Printer List testi...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/printers/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Printer list testi tamamlandı${NC}"
echo ""

# Test 2: Printer Scan
echo -e "${YELLOW}3. Printer Scan testi...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/printers/scan/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Printer scan testi tamamlandı${NC}"
echo ""

# Test 3: Create Printer
echo -e "${YELLOW}4. Create Printer testi...${NC}"
CREATE_RESPONSE=$(curl -s -X POST "$BASE_URL/printers/" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test API Printer",
    "ip_address": "192.168.1.199",
    "port": 9100,
    "description": "API test üçün yaradılıb",
    "is_main": false
  }')

PRINTER_ID=$(echo $CREATE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$PRINTER_ID" ]; then
    echo -e "${RED}✗ Printer yaradıla bilmədi!${NC}"
    echo "Response: $CREATE_RESPONSE"
else
    echo -e "${GREEN}✓ Printer yaradıldı (ID: $PRINTER_ID)${NC}"
    echo "Response: $CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null
fi
echo ""

# Test 4: Get Printer Detail
if [ ! -z "$PRINTER_ID" ]; then
    echo -e "${YELLOW}5. Printer Detail testi (ID: $PRINTER_ID)...${NC}"
    RESPONSE=$(curl -s -X GET "$BASE_URL/printers/$PRINTER_ID/" \
      -H "Authorization: Token $TOKEN")
    echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo -e "${GREEN}✓ Printer detail testi tamamlandı${NC}"
    echo ""
fi

# Test 5: Update Printer
if [ ! -z "$PRINTER_ID" ]; then
    echo -e "${YELLOW}6. Update Printer testi (PATCH)...${NC}"
    RESPONSE=$(curl -s -X PATCH "$BASE_URL/printers/$PRINTER_ID/" \
      -H "Authorization: Token $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{
        "name": "Yenilənmiş Test Printer"
      }')
    echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo -e "${GREEN}✓ Printer update testi tamamlandı${NC}"
    echo ""
fi

# Test 6: Get Main Printer
echo -e "${YELLOW}7. Get Main Printer testi...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/printers/main-printer/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Main printer testi tamamlandı${NC}"
echo ""

# Test 7: Test Print
if [ ! -z "$PRINTER_ID" ]; then
    echo -e "${YELLOW}8. Test Print testi...${NC}"
    RESPONSE=$(curl -s -X POST "$BASE_URL/printers/test-print/" \
      -H "Authorization: Token $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"printer_id\": $PRINTER_ID
      }")
    echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo -e "${GREEN}✓ Test print testi tamamlandı${NC}"
    echo ""
fi

# Test 8: Preparation Place List
echo -e "${YELLOW}9. Preparation Place List testi...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/preparation-places/" \
  -H "Authorization: Token $TOKEN")
echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Preparation place list testi tamamlandı${NC}"
echo ""

# Test 9: Create Preparation Place
if [ ! -z "$PRINTER_ID" ]; then
    echo -e "${YELLOW}10. Create Preparation Place testi...${NC}"
    CREATE_PLACE_RESPONSE=$(curl -s -X POST "$BASE_URL/preparation-places/" \
      -H "Authorization: Token $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"name\": \"Test API Hazırlama Yeri\",
        \"printer\": $PRINTER_ID
      }")
    
    PLACE_ID=$(echo $CREATE_PLACE_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
    
    if [ -z "$PLACE_ID" ]; then
        echo -e "${RED}✗ Hazırlanma yeri yaradıla bilmədi!${NC}"
        echo "Response: $CREATE_PLACE_RESPONSE"
    else
        echo -e "${GREEN}✓ Hazırlanma yeri yaradıldı (ID: $PLACE_ID)${NC}"
        echo "Response: $CREATE_PLACE_RESPONSE" | python3 -m json.tool 2>/dev/null
    fi
    echo ""
fi

# Test 10: Receipt List
echo -e "${YELLOW}11. Receipt List testi...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/receipts/?ordering=-created_at" \
  -H "Authorization: Token $TOKEN")
echo "Response (ilk 5 sətir):"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null | head -20 || echo "$RESPONSE" | head -20
echo -e "${GREEN}✓ Receipt list testi tamamlandı${NC}"
echo ""

# Test 11: Search Printer
echo -e "${YELLOW}12. Search Printer testi...${NC}"
RESPONSE=$(curl -s -X GET "$BASE_URL/printers/?search=Test" \
  -H "Authorization: Token $TOKEN")
echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo -e "${GREEN}✓ Search testi tamamlandı${NC}"
echo ""

# Clean up - Delete created resources
if [ ! -z "$PLACE_ID" ]; then
    echo -e "${YELLOW}13. Təmizləmə: Hazırlanma yeri silinir...${NC}"
    curl -s -X DELETE "$BASE_URL/preparation-places/$PLACE_ID/" \
      -H "Authorization: Token $TOKEN" > /dev/null
    echo -e "${GREEN}✓ Hazırlanma yeri silindi${NC}"
fi

if [ ! -z "$PRINTER_ID" ]; then
    echo -e "${YELLOW}14. Təmizləmə: Printer silinir...${NC}"
    RESPONSE=$(curl -s -X DELETE "$BASE_URL/printers/$PRINTER_ID/" \
      -H "Authorization: Token $TOKEN")
    echo "Response: $RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo -e "${GREEN}✓ Printer silindi${NC}"
fi

echo ""
echo "======================================"
echo -e "${GREEN}   BÜTÜN TESTLƏR TAMAMLANDI!${NC}"
echo "======================================"
