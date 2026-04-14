import pytest
from app import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    res = client.get('/health')
    assert res.status_code == 200
    assert res.get_json()['status'] == 'UP'


def test_home(client):
    res = client.get('/')
    assert res.status_code == 200


def test_users(client):
    res = client.get('/users')
    assert res.status_code == 200


def test_health_returns_json(client):
    res = client.get('/health')
    assert res.content_type == 'application/json'


def test_home_returns_message(client):
    res = client.get('/')
    data = res.get_json()
    assert 'message' in data


def test_home_returns_environment(client):
    res = client.get('/')
    data = res.get_json()
    assert 'environment' in data


def test_home_returns_db_host(client):
    res = client.get('/')
    data = res.get_json()
    assert 'db_host' in data


def test_health_status_value(client):
    res = client.get('/health')
    assert res.get_json()['status'] == 'UP'
