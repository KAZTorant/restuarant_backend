#!/usr/bin/env python3
import json

import requests

BASE_URL = "http://localhost:8000"

# 1. Login
print("=== 1. Login ===")
login_response = requests.post(
    f"{BASE_URL}/api/admin/auth/login/",
    json={"username": "devUser", "password": "banm1234"}
)
print(f"Status: {login_response.status_code}")
if login_response.status_code == 200:
    token = login_response.json()['token']
    print(f"Token: {token[:50]}...")
    headers = {"Authorization": f"Bearer {token}"}
else:
    print(login_response.text)
    exit(1)

# 2. Meal Groups
print("\n=== 2. Meal Groups ===")
groups_response = requests.get(f"{BASE_URL}/api/admin/meals/groups/", headers=headers)
print(f"Status: {groups_response.status_code}")
if groups_response.status_code == 200:
    groups = groups_response.json()
    print(f"Count: {len(groups) if isinstance(groups, list) else 'N/A'}")
    print(json.dumps(groups, indent=2, ensure_ascii=False)[:500])
else:
    print(groups_response.text)

# 3. Meal Categories
print("\n=== 3. Meal Categories ===")
categories_response = requests.get(f"{BASE_URL}/api/admin/meals/categories/", headers=headers)
print(f"Status: {categories_response.status_code}")
if categories_response.status_code == 200:
    categories = categories_response.json()
    print(f"Count: {len(categories) if isinstance(categories, list) else 'N/A'}")
    print(json.dumps(categories, indent=2, ensure_ascii=False)[:500])
else:
    print(categories_response.text)

# 4. Meals
print("\n=== 4. Meals ===")
meals_response = requests.get(f"{BASE_URL}/api/admin/meals/meals/", headers=headers)
print(f"Status: {meals_response.status_code}")
if meals_response.status_code == 200:
    meals = meals_response.json()
    print(f"Count: {len(meals) if isinstance(meals, list) else 'N/A'}")
    print(json.dumps(meals, indent=2, ensure_ascii=False)[:800])
else:
    print(meals_response.text)

# 5. Test CRUD - Create Meal Group
print("\n=== 5. Create Meal Group ===")
create_group = requests.post(
    f"{BASE_URL}/api/admin/meals/groups/",
    headers=headers,
    json={"name": "Test Qrup", "description": "Test üçün yaradılmış qrup"}
)
print(f"Status: {create_group.status_code}")
print(json.dumps(create_group.json(), indent=2, ensure_ascii=False))

if create_group.status_code == 201:
    group_id = create_group.json()['id']
    
    # 6. Get single group
    print(f"\n=== 6. Get Group {group_id} ===")
    get_group = requests.get(f"{BASE_URL}/api/admin/meals/groups/{group_id}/", headers=headers)
    print(f"Status: {get_group.status_code}")
    print(json.dumps(get_group.json(), indent=2, ensure_ascii=False))
    
    # 7. Update group
    print(f"\n=== 7. Update Group {group_id} ===")
    update_group = requests.patch(
        f"{BASE_URL}/api/admin/meals/groups/{group_id}/",
        headers=headers,
        json={"description": "Yenilənmiş təsvir"}
    )
    print(f"Status: {update_group.status_code}")
    print(json.dumps(update_group.json(), indent=2, ensure_ascii=False))
    
    # 8. Delete group
    print(f"\n=== 8. Delete Group {group_id} ===")
    delete_group = requests.delete(f"{BASE_URL}/api/admin/meals/groups/{group_id}/", headers=headers)
    print(f"Status: {delete_group.status_code}")
    if delete_group.status_code == 204:
        print("✅ Uğurla silindi!")
    elif delete_group.status_code == 400:
        print(f"❌ Silinə bilməz: {delete_group.json()}")
