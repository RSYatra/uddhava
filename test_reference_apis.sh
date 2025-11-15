#!/bin/bash
# Test script for Reference Data API endpoints
#
# Usage:
#   1. First login to get JWT token:
#      export JWT_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
#        -H "Content-Type: application/json" \
#        -d '{"email": "YOUR_EMAIL", "password": "YOUR_PASSWORD"}' | \
#        python3 -c "import sys, json; print(json.load(sys.stdin)['data']['access_token'])")
#
#   2. Then run this script:
#      ./test_reference_apis.sh

BASE_URL="http://localhost:8000/api/v1"

if [ -z "$JWT_TOKEN" ]; then
    echo "ERROR: JWT_TOKEN not set!"
    echo ""
    echo "Please login first:"
    echo "  export JWT_TOKEN=\$(curl -s -X POST $BASE_URL/auth/login \\"
    echo "    -H \"Content-Type: application/json\" \\"
    echo "    -d '{\"email\": \"YOUR_EMAIL\", \"password\": \"YOUR_PASSWORD\"}' | \\"
    echo "    python3 -c \"import sys, json; print(json.load(sys.stdin)['data']['access_token'])\")"
    exit 1
fi

echo "=========================================="
echo "Testing Reference Data API Endpoints"
echo "=========================================="
echo ""

# Test 1: Centers - All
echo "1. GET /api/v1/centers/ (All centers - should return 180)"
curl -s -X GET "$BASE_URL/centers/" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\")"
echo ""

# Test 2: Centers - Search by "India"
echo "2. GET /api/v1/centers/?search=India (Filter by 'India')"
curl -s -X GET "$BASE_URL/centers/?search=India" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); print('First 3 results:'); [print(f\"  - {c['city']}, {c['state_province']}, {c['country']}\") for c in data['data'][:3]]"
echo ""

# Test 3: Centers - Search by "M"
echo "3. GET /api/v1/centers/?search=M (Prefix search - starts with 'M')"
curl -s -X GET "$BASE_URL/centers/?search=M" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); print('First 5 results:'); [print(f\"  - {c['city']}, {c['country']}\") for c in data['data'][:5]]"
echo ""

# Test 4: Country Codes - All
echo "4. GET /api/v1/country-codes/ (All countries - should return 240)"
curl -s -X GET "$BASE_URL/country-codes/" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\")"
echo ""

# Test 5: Country Codes - Search by "IN"
echo "5. GET /api/v1/country-codes/?search=IN (Filter by 'IN' prefix)"
curl -s -X GET "$BASE_URL/country-codes/?search=IN" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); print('Results:'); [print(f\"  - {c['country']} ({c['alpha2']}, {c['alpha3']}, +{c['code']})\") for c in data['data']]"
echo ""

# Test 6: Country Codes - Search by "United"
echo "6. GET /api/v1/country-codes/?search=United (Filter by 'United' prefix)"
curl -s -X GET "$BASE_URL/country-codes/?search=United" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); print('Results:'); [print(f\"  - {c['country']}\") for c in data['data']]"
echo ""

# Test 7: Spiritual Masters - All
echo "7. GET /api/v1/spiritual-masters/ (All spiritual masters - should return 127)"
curl -s -X GET "$BASE_URL/spiritual-masters/" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); accepting = sum(1 for m in data['data'] if m['accepting_disciples']); print(f\"Accepting disciples: {accepting}/{len(data['data'])}\")"
echo ""

# Test 8: Spiritual Masters - Search by "HH Radh"
echo "8. GET /api/v1/spiritual-masters/?search=HH%20Radh (Filter by 'HH Radh' prefix)"
curl -s -X GET "$BASE_URL/spiritual-masters/?search=HH%20Radh" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); print('Results:'); [print(f\"  - {m['name']} ({m['initials']}) - Accepting: {m['accepting_disciples']}\") for m in data['data']]"
echo ""

# Test 9: Spiritual Masters - Search by initials "RNS"
echo "9. GET /api/v1/spiritual-masters/?search=RNS (Filter by initials 'RNS')"
curl -s -X GET "$BASE_URL/spiritual-masters/?search=RNS" \
  -H "Authorization: Bearer $JWT_TOKEN" | \
  python3 -c "import sys, json; data = json.load(sys.stdin); print(f\"Success: {data['success']}, Count: {len(data['data'])}, Message: {data['message']}\"); print('Results:'); [print(f\"  - {m['name']} ({m['initials']})\") for m in data['data']]"
echo ""

echo "=========================================="
echo "All tests completed!"
echo "=========================================="
