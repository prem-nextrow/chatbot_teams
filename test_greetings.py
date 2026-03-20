import requests
import json

def test_message(message):
    print(f"\n{'='*80}")
    print(f"Testing: '{message}'")
    print('='*80)
    
    response = requests.post(
        "http://localhost:8003/chat",
        json={"message": message, "session_id": "test"}
    )
    
    if response.status_code == 200:
        data = response.json()
        reply = data['reply']
        print(f"✅ Status: {response.status_code}")
        
        # Check if it lists reports
        if "Available Reports:" in reply or "chevy-report" in reply:
            print("✅ LISTS REPORTS")
        else:
            print("❌ DOES NOT LIST REPORTS")
        
        print(f"\n📝 Reply (first 300 chars):\n{reply[:300]}...")
    else:
        print(f"❌ Status: {response.status_code}")
        print(f"Error: {response.text}")

# Test various greetings
test_message("hi")
test_message("hello")
test_message("hey")
test_message("Hi there")
test_message("Hello!")
test_message("Good morning")
test_message("")  # Empty message
test_message("list reports")
test_message("analyze hyatt")
