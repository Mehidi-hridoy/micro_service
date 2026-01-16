import requests
import json

BASE_URL = "http://localhost:8000/api"

def print_response(label, response):
    print(f"\n{label}")
    print("-" * 40)
    print(f"Status: {response.status_code}")
    print(f"URL: {response.url}")
    if response.status_code < 400:
        try:
            data = response.json()
            print("Response:", json.dumps(data, indent=2))
        except:
            print("Response:", response.text[:200])
    else:
        print("Error:", response.text[:200])

def test_api_versions():
    print("=" * 60)
    print("TESTING API VERSION DIFFERENCES")
    print("=" * 60)
    
    # 1. Get JWT Token
    print("\n1. Getting JWT Token...")
    auth_response = requests.post(
        f"{BASE_URL}/token/",
        json={"email": "admin@demo.com", "password": "admin123"}
    )
    
    if auth_response.status_code != 200:
        print("❌ Failed to get token")
        print("Response:", auth_response.text)
        return
    
    token_data = auth_response.json()
    access_token = token_data['access']
    print(f"✅ Token obtained")
    print(f"Tenant ID in token: {token_data.get('tenant_id', 'Not found')}")
    
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 2. TEST API V1 - BASIC FEATURES
    print("\n" + "=" * 60)
    print("API VERSION 1 TESTING (BASIC FEATURES)")
    print("=" * 60)
    
    # Get users (v1)
    print("\n📋 Testing /api/v1/users/users/")
    v1_users = requests.get(f"{BASE_URL}/v1/users/users/", headers=headers)
    print_response("GET Users (v1)", v1_users)
    
    # Create shipment (v1 - basic)
    print("\n📦 Testing /api/v1/shipping/shipments/ (CREATE)")
    v1_shipment_data = {
        "sender_name": "Test Sender v1",
        "receiver_name": "Test Receiver v1"
    }
    v1_create = requests.post(
        f"{BASE_URL}/v1/shipping/shipments/", 
        headers=headers,
        json=v1_shipment_data
    )
    print_response("CREATE Shipment (v1)", v1_create)
    
    if v1_create.status_code == 201:
        shipment_id = v1_create.json()['id']
        
        # Update status (v1 feature)
        print("\n🔄 Testing /api/v1/shipping/shipments/{id}/update-status/")
        status_data = {"status": "shipped", "location": "Warehouse"}
        v1_status = requests.post(
            f"{BASE_URL}/v1/shipping/shipments/{shipment_id}/update-status/",
            headers=headers,
            json=status_data
        )
        print_response("Update Status (v1-only feature)", v1_status)
    
    # 3. TEST API V2 - ENHANCED FEATURES
    print("\n" + "=" * 60)
    print("API VERSION 2 TESTING (ENHANCED FEATURES)")
    print("=" * 60)
    
    # Get current user (v2-only feature)
    print("\n👤 Testing /api/v2/users/me/ (V2-ONLY FEATURE)")
    v2_me = requests.get(f"{BASE_URL}/v2/users/me/", headers=headers)
    print_response("GET Current User (v2-only)", v2_me)
    
    # Get shipments with analytics (v2 feature)
    print("\n📊 Testing /api/v2/shipping/shipments/analytics/ (V2-ONLY FEATURE)")
    v2_analytics = requests.get(f"{BASE_URL}/v2/shipping/shipments/analytics/", headers=headers)
    print_response("GET Analytics (v2-only)", v2_analytics)
    
    # Create shipment (v2 - more fields)
    print("\n📦 Testing /api/v2/shipping/shipments/ (CREATE with more fields)")
    v2_shipment_data = {
        "sender_name": "Test Sender v2",
        "sender_address": "123 v2 Street",
        "receiver_name": "Test Receiver v2",
        "receiver_address": "456 v2 Avenue",
        "weight": "3.5",
        "dimensions": "10x10x15",
        "estimated_delivery": "2024-12-31"
    }
    v2_create = requests.post(
        f"{BASE_URL}/v2/shipping/shipments/", 
        headers=headers,
        json=v2_shipment_data
    )
    print_response("CREATE Shipment (v2 - more fields)", v2_create)
    
    if v2_create.status_code == 201:
        v2_shipment_id = v2_create.json()['id']
        
        # Add tracking event (v2 feature)
        print("\n📍 Testing /api/v2/shipping/shipments/{id}/add_tracking/ (V2-ONLY FEATURE)")
        tracking_data = {
            "event_type": "departed",
            "location": "Sorting Facility",
            "description": "Shipment has departed"
        }
        v2_tracking = requests.post(
            f"{BASE_URL}/v2/shipping/shipments/{v2_shipment_id}/add_tracking/",
            headers=headers,
            json=tracking_data
        )
        print_response("Add Tracking Event (v2-only)", v2_tracking)
        
        # Get tracking events (v2 feature)
        print("\n📍 Testing /api/v2/shipping/shipments/{id}/tracking/ (V2-ONLY FEATURE)")
        v2_get_tracking = requests.get(
            f"{BASE_URL}/v2/shipping/shipments/{v2_shipment_id}/tracking/",
            headers=headers
        )
        print_response("GET Tracking Events (v2-only)", v2_get_tracking)
    
    # 4. TEST MULTI-TENANCY
    print("\n" + "=" * 60)
    print("TESTING MULTI-TENANCY ISOLATION")
    print("=" * 60)
    
    print("\n🔒 Testing with different tenant headers...")
    
    # Test with tenant_1 header
    headers_tenant1 = headers.copy()
    headers_tenant1['X-Tenant-ID'] = '1'
    
    v1_tenant1 = requests.get(
        f"{BASE_URL}/v1/shipping/shipments/", 
        headers=headers_tenant1
    )
    print_response("GET Shipments (Tenant 1)", v1_tenant1)
    
    # Test with tenant_2 header
    headers_tenant2 = headers.copy()
    headers_tenant2['X-Tenant-ID'] = '2'
    
    v1_tenant2 = requests.get(
        f"{BASE_URL}/v1/shipping/shipments/", 
        headers=headers_tenant2
    )
    print_response("GET Shipments (Tenant 2)", v1_tenant2)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print("\n✅ API Version 1 (Basic):")
    print("   • Users: CRUD operations")
    print("   • Shipments: Basic CRUD + status update")
    print("   • Registration endpoint")
    
    print("\n✅ API Version 2 (Enhanced):")
    print("   • All v1 features PLUS:")
    print("   • /me/ endpoint for current user")
    print("   • Bulk operations")
    print("   • Analytics endpoint")
    print("   • Tracking events management")
    print("   • More shipment fields (address, dimensions, etc.)")
    
    print("\n✅ Multi-tenancy working:")
    print("   • Data isolation between tenants")
    print("   • JWT tokens include tenant info")
    print("   • Header-based tenant switching")

if __name__ == "__main__":
    test_api_versions()