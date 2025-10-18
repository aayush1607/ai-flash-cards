#!/usr/bin/env python3
"""
Test the API endpoint directly
"""
import requests
import json

def test_api():
    """Test the topic feed API"""
    try:
        response = requests.get("http://localhost:8000/api/topic-feed?q=coffee&timeframe=30d")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Items found: {len(data.get('items', []))}")
            if data.get('items'):
                print(f"First item: {data['items'][0]['title']}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
