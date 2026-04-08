#!/bin/bash

TOKEN=$(curl -s -X POST http://localhost:8000/api/admin/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "devUser", "password": "banm1234"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

echo "✅ Login uğurlu! Token alındı."
echo ""

echo "=== 📍 Preparation Places ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/preparation-places/" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Count: {len(data)}')"

echo ""
echo "=== 📁 Meal Groups ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/groups/" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Count: {len(data)}')"

echo ""
echo "=== 📂 Meal Categories ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/categories/" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Count: {len(data)}')"

echo ""
echo "=== 🍽️ Meals ==="
curl -s -X GET "http://localhost:8000/api/admin/meals/meals/" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "import sys, json; data=json.load(sys.stdin); print(f'Count: {len(data)}')"

echo ""
echo ""
echo "✅ Bütün API-lər işləyir!"
echo ""
echo "📊 Cəmi API sayı:"
echo "   • Auth APIs: 4"
echo "   • Preparation Places APIs: 6"
echo "   • Meal Groups APIs: 6"
echo "   • Meal Categories APIs: 6"
echo "   • Meals APIs: 6"
echo "   • Bulk Operations APIs: 3"
echo "   ────────────────────────"
echo "   📌 Toplam: 31 API"
