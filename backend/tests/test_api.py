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


def test_queue_limit_and_failed_jobs(tmp_path, monkeypatch):
    import threading
    import qubitguard.api as api_module
    entered = threading.Event()
    release = threading.Event()

    def fail_after_release(config, progress):
        entered.set()
        assert release.wait(timeout=10)
        raise RuntimeError('test internal detail')

    monkeypatch.setattr(api_module, 'run_experiment', fail_after_release)
    with TestClient(create_app(str(tmp_path / 'queue.sqlite'))) as client:
        try:
            ids = []
            for _ in range(4):
                response = client.post('/api/experiments', json={'distances':[3], 'physical_error_rates':[0.01], 'shots':100})
                assert response.status_code == 202
                ids.append(response.json()['id'])
            assert entered.wait(timeout=2)
            assert client.post('/api/experiments', json={}).status_code == 429
            assert client.get(f'/api/experiments/{ids[0]}/export').status_code == 409
        finally:
            release.set()
        for _ in range(200):
            items = [client.get('/api/experiments/' + key).json() for key in ids]
            if all(item['status'] == 'failed' for item in items):
                break
            time.sleep(0.01)
        assert all(item['status'] == 'failed' for item in items)
        assert all('internal detail' not in item['error'] for item in items)
