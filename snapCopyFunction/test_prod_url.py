#!/usr/bin/env python
import requests
import sys

url = 'https://f8do9lswp5.execute-api.ap-southeast-2.amazonaws.com/prod'
try:
    resp = requests.get(url, timeout=10)
    print('Status:', resp.status_code)
    print('Headers:', resp.headers)
    # Check if stage is prod in the HTML
    if 'prod' in resp.text.lower():
        print('Stage detection: prod')
    else:
        print('Stage detection: unknown')
    # Print first 500 chars
    print('Preview:', resp.text[:500])
except Exception as e:
    print('Error:', e)
    sys.exit(1)