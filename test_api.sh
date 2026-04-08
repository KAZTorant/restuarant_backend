#!/bin/bash

TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "devUser", "password": "banm1234"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "Token: $TOKEN"
echo ""

echo "=== 1. Meal Groups List ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/groups/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "=== 2. Meal Categories List ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/categories/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""

echo "=== 3. Meals List ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/meals/" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | head -100
echo ""

echo "=== 4. Create Meal Group ==="
GROUP_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/admin/meals/groups/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Qrup API", "description": "API test üçün"}')
echo "$GROUP_RESPONSE" | python3 -m json.tool
GROUP_ID=$(echo "$GROUP_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo ""

if [ ! -z "$GROUP_ID" ]; then
    echo "=== 5. Get Group $GROUP_ID ==="
    curl -s -X GET "http://localhost:8000/api/admin/meals/groups/$GROUP_ID/" \
      -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
    echo ""
    
    echo "=== 6. Update Group $GROUP_ID ==="
    curl -s -X PATCH "http://localhost:8000/api/admin/meals/groups/$GROUP_ID/" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"description": "Yenilənmiş təsvir"}' | python3 -m json.tool
    echo ""
    
    echo "=== 7. Delete Group $GROUP_ID ==="
    curl -s -X DELETE "http://localhost:8000/api/admin/meals/groups/$GROUP_ID/" \
      -H "Authorization: Bearer $TOKEN" -w "\nStatus: %{http_code}\n"
fi
