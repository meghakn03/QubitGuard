"""Exercise a running Compose app through its public Nginx entrypoint."""
import json
import os
import time
import urllib.request

BASE = 'http://127.0.0.1:' + os.getenv('QUBITGUARD_PORT', '8766')


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=10) as response:
        return response.read()


assert b'root' in get('/')
assert json.loads(get('/api/health'))['status'] == 'ok'
request = urllib.request.Request(BASE + '/api/experiments',
    data=json.dumps({'name': 'Compose smoke check', 'distances': [3], 'physical_error_rates': [0.01], 'shots': 100}).encode(),
    headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(request, timeout=10) as response:
    assert response.status == 202
    key = json.load(response)['id']
for _ in range(100):
    run = json.loads(get('/api/experiments/' + key))
    if run['status'] in ('completed', 'failed'):
        break
    time.sleep(0.1)
assert run['status'] == 'completed', run
assert b'logical_error_rate' in get(f'/api/experiments/{key}/export?format=csv')
assert json.loads(get(f'/api/experiments/{key}/export'))['result']['results']
print(f'Compose smoke passed: Nginx, API, simulation, SQLite and exports ({key})')
