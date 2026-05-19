import urllib.request
import json
import base64
import time

BASE = 'http://127.0.0.1:8000'

def act(action):
    req = urllib.request.Request(
        f'{BASE}/act',
        data=json.dumps({'action': action}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    return urllib.request.urlopen(req).read().decode()

def screenshot():
    req = urllib.request.Request(
        f'{BASE}/screenshot_annotated',
        data=b'',
        headers={'Content-Type': 'application/json'}
    )
    resp = json.loads(urllib.request.urlopen(req).read().decode())
    with open('manual_current.jpg', 'wb') as f:
        f.write(base64.b64decode(resp['image']))
    print('Saved manual_current.jpg')
    print('Elements:', len(resp['elements']))
    for k, v in list(resp['elements'].items())[:25]:
        tag = v.get('tag', '')
        text = v.get('text', '')
        print(f'  {k:>2s}. [{tag:10s}] {text[:40]}')
    return resp

# Click "Create article" (current ID 25)
print(act({'action_type': 'click', 'element_display_id': 25}))
time.sleep(2)
screenshot()
