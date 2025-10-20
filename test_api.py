#!/usr/bin/env python3
"""
Quick API test script - run this in a separate terminal
"""
import requests
import json

def test_api():
    try:
        # Test morning brief
        print("Testing Morning Brief API...")
        response = requests.get("http://localhost:8001/api/morning-brief")
        data = response.json()
        
        print(f"✅ Morning Brief: {len(data['items'])} articles found")
        if data['items']:
            print(f"   First article: {data['items'][0]['title'][:50]}...")
        
        # Test topic feed
        print("\nTesting Topic Feed API...")
        response = requests.get("http://localhost:8001/api/topic-feed?q=AI")
        data = response.json()
        
        print(f"✅ Topic Feed: {len(data['items'])} articles found")
        
        # Test health
        print("\nTesting Health API...")
        response = requests.get("http://localhost:8001/api/health")
        data = response.json()
        
        print(f"✅ Health: Database has {data['database']['article_count']} articles")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_api()
