#!/usr/bin/env python3
import requests
import time

# Wait for server to start
time.sleep(3)

# Test word-categories endpoint
try:
    resp = requests.get('http://localhost:8001/word-categories')
    print('Word categories response:', resp.json())
except Exception as e:
    print('Error testing word-categories:', e)

# Test daily-pack endpoint
try:
    resp = requests.get('http://localhost:8001/daily-pack?limit=2&level=A1')
    print('Daily pack response:', resp.json())
except Exception as e:
    print('Error testing daily-pack:', e)