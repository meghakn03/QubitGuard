import csv
import io
import time

from fastapi.testclient import TestClient
from qubitguard.api import create_app
from qubitguard.store import Store


def test_persistent_experiment_lifecycle_and_exports(tmp_path):
    path = str(tmp_path / "test.sqlite")
    with TestClient(create_app(path)) as client:
        assert client.get('/api/health').json()['status'] == 'ok'
        config = dict(distances=[3], physical_error_rates=[0.03], shots=100)
        response = client.post('/api/experiments', json=config)
        assert response.status_code == 202
        key = response.json()['id']
        for _ in range(200):
            item = client.get(f'/api/experiments/{key}').json()
            if item['status'] in ('completed', 'failed'):
                break
            time.sleep(0.01)
        assert item['status'] == 'completed', item
        assert item['progress'] == 100
        assert len(client.get('/api/experiments').json()) == 1
        exported = client.get(f'/api/experiments/{key}/export').json()
        assert exported['result']['results'] == item['result']['results']
        csv_response = client.get(f'/api/experiments/{key}/export?format=csv')
        rows = list(csv.DictReader(io.StringIO(csv_response.text)))
        assert len(rows) == 2
        assert rows[0]['decoder'] == 'mwpm'
        assert 'OBSERVABLE_INCLUDE' in client.get(f'/api/experiments/{key}/circuit?distance=3&physical_error_rate=0.03').text
        assert client.get(f'/api/experiments/{key}/circuit?distance=5&physical_error_rate=0.03').status_code == 422
    with TestClient(create_app(path)) as client:
        assert client.get(f'/api/experiments/{key}').json()['status'] == 'completed'
        assert client.get('/api/experiments/missing').status_code == 404
        assert client.post('/api/experiments', json={'code':'surface_z'}).status_code == 422
        assert client.get('/api/experiments?limit=0').status_code == 422


def test_recover_interrupted_jobs(tmp_path):
    store = Store(str(tmp_path / 'recovery.sqlite'))
    key = store.create({'name':'interrupted'})
    store.update(key, status='running')
    store.recover()
    assert store.get(key)['status'] == 'failed'
    assert 'restarted' in store.get(key)['error']
