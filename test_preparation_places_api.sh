#!/bin/bash

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "devUser", "password": "banm1234"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "Token: $TOKEN"
echo ""

echo "=== 1. Get All Preparation Places ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/preparation-places/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "=== 2. Create Preparation Place ==="
PLACE_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/admin/meals/preparation-places/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Hazırlanma Yeri", "printer": null}')
echo "$PLACE_RESPONSE" | python3 -m json.tool
PLACE_ID=$(echo "$PLACE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo ""

if [ ! -z "$PLACE_ID" ]; then
    echo "=== 3. Get Single Preparation Place $PLACE_ID ==="
    curl -s -X GET "http://localhost:8000/api/admin/meals/preparation-places/$PLACE_ID/" \
      -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
    echo ""
    
    echo "=== 4. Update Preparation Place $PLACE_ID ==="
    curl -s -X PATCH "http://localhost:8000/api/admin/meals/preparation-places/$PLACE_ID/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"name": "Yenilənmiş Hazırlanma Yeri"}' | python3 -m json.tool
    echo ""
    
    echo "=== 5. Delete Preparation Place $PLACE_ID ==="
    curl -s -X DELETE "http://localhost:8000/api/admin/meals/preparation-places/$PLACE_ID/" \
      -H "Authorization: Bearer $TOKEN" -w "\nStatus: %{http_code}\n"
fi
