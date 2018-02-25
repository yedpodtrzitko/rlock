import json

import arrow
import pytest

from ..lock import get_lock
from .conftest import USERID, CHANNEL
from ..webserver import app
from .. import tasker
from .. import slackbot
from .. import webserver


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    monkeypatch.setattr(webserver, "channel_message", lambda *args, **kwargs: True)
    monkeypatch.setattr(slackbot, "channel_message", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasker, "channel_message", lambda *args, **kwargs: True)


def test_obtain_lock(clean_redis, req_data):
    request, response = app.test_client.post('/lock', data=req_data)
    assert response.status == 204
    lock_user = clean_redis.hget(f'channel_{CHANNEL}', 'user_id')
    assert lock_user.decode('utf-8') == USERID


def test_unlock(owned_redis, req_data):
    request, response = app.test_client.post('/unlock', data=req_data)
    assert response.status == 204


def test_lock_nonowned(nonowned_redis, req_data):
    request, response = app.test_client.post('/lock', data=req_data)
    assert response.text.startswith('Cant lock - currently locked by ')


def test_unlock_nonowned(nonowned_redis, req_data):
    request, response = app.test_client.post('/unlock', data=req_data)
    assert response.text.startswith('Cant unlock, locked by ')


def test_overwrite_expired_lock(clean_redis, req_data):
    clean_redis.hmset(f'channel_{CHANNEL}', {
        'user_id': USERID * 2,
        'expiry_tstamp': arrow.now().shift(minutes=-1).timestamp,
    })

    request, response = app.test_client.post('/lock', data=req_data)
    assert response.status == 204
    lock_user = clean_redis.hget(f'channel_{CHANNEL}', 'user_id')
    assert lock_user.decode('utf-8') == USERID


def test_dialock_unlock(owned_redis, owned_lock, dialock_data):
    req_data = {
        'payload': [
            json.dumps(dialock_data),
        ]
    }

    request, response = app.test_client.post('/dialock', data=req_data)
    assert response.status == 204
    assert not get_lock(owned_lock.full_id, True)


def test_dialock_extend(owned_redis, owned_lock, dialock_data):
    dialock_data['actions'][0]['value'] = 'lock'
    req_data = {
        'payload': [
            json.dumps(dialock_data)
        ]
    }

    request, response = app.test_client.post('/dialock', data=req_data)
    assert response.status == 204

    lock = get_lock(owned_lock.full_id, True)
    assert not lock.user_notified
    assert not lock.is_expiring


def test_dialock_nonowned_unlock(nonowned_redis, nonowned_lock, dialock_data):
    req_data = {
        'payload': [
            json.dumps(dialock_data),
        ]
    }

    request, response = app.test_client.post('/dialock', data=req_data)
    assert response.status == 200
    assert response.text.startswith('Cant unlock, locked by')
    assert get_lock(nonowned_lock.full_id, True)
