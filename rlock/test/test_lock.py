import json

import arrow
import pytest

from .. import slackbot, tasker, webserver
from ..lock import add_lock_subscriber, get_lock, get_lock_subscribers
from ..webserver import app, get_unlock_message
from .conftest import CHANNEL, OTHER_USERID, SET_EXPIRY, USERID


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    monkeypatch.setattr(webserver, "channel_message", lambda *args, **kwargs: True)
    monkeypatch.setattr(slackbot, "channel_message", lambda *args, **kwargs: True)
    monkeypatch.setattr(tasker, "channel_message", lambda *args, **kwargs: True)


def test_obtain_lock(req_data):
    request, response = app.test_client.post('/lock', data=req_data)
    assert response.status == 204
    assert get_lock(CHANNEL).user_id == USERID


def test_extend_lock(owned_redis, req_data):
    lock = get_lock(CHANNEL)
    assert lock.expiry_tstamp == SET_EXPIRY

    request, response = app.test_client.post('/lock', data=req_data)
    assert response.status == 204
    lock = get_lock(CHANNEL)
    assert lock.user_id == USERID
    assert lock.expiry_tstamp == SET_EXPIRY + (30 * 60)


def test_unlock(owned_redis, req_data):
    request, response = app.test_client.post('/unlock', data=req_data)
    assert response.status == 204
    assert not get_lock(CHANNEL)


def test_lock_nonowned(nonowned_redis, req_data):
    request, response = app.test_client.post('/lock', data=req_data)
    assert response.text == 'Currently locked, I will ping you when the lock will expire.'

    lock = get_lock(CHANNEL)
    assert lock.user_id == OTHER_USERID
    lock_subs = get_lock_subscribers(lock)
    assert lock_subs == [USERID]


def test_unlock_nonowned(nonowned_redis, req_data):
    request, response = app.test_client.post('/unlock', data=req_data)
    assert response.text.startswith('Cant unlock, locked by ')


def test_overwrite_expired_lock(clean_redis, req_data):
    clean_redis.hmset(f'channel_{CHANNEL}', {
        'user_id': OTHER_USERID,
        'expiry_tstamp': arrow.now().shift(minutes=-1).timestamp,
    })

    request, response = app.test_client.post('/lock', data=req_data)
    assert response.status == 204
    assert get_lock(CHANNEL).user_id == USERID


def test_dialock_unlock(owned_redis, dialock_data):
    req_data = {
        'payload': [
            json.dumps(dialock_data),
        ]
    }

    request, response = app.test_client.post('/dialock', data=req_data)
    assert response.status == 204
    assert not get_lock(CHANNEL)


def test_dialock_extend(owned_redis, dialock_data):
    dialock_data['actions'][0]['value'] = 'lock'
    req_data = {
        'payload': [
            json.dumps(dialock_data),
        ]
    }

    lock = get_lock(CHANNEL)
    assert lock.expiry_tstamp == SET_EXPIRY
    assert lock.is_expiring

    request, response = app.test_client.post('/dialock', data=req_data)
    assert response.status == 204

    lock = get_lock(CHANNEL)
    assert not lock.user_notified
    assert not lock.is_expiring
    assert lock.expiry_tstamp == SET_EXPIRY + (30 * 60)


def test_dialock_nonowned_unlock(nonowned_redis, dialock_data):
    req_data = {
        'payload': [
            json.dumps(dialock_data),
        ]
    }

    request, response = app.test_client.post('/dialock', data=req_data)
    assert response.status == 200
    assert response.text.startswith('Cant unlock, locked by')
    assert get_lock(CHANNEL)


def test_get_unlock_message(owned_redis, owned_lock):
    add_lock_subscriber(owned_lock, 'foo')
    add_lock_subscriber(owned_lock, 'bar')
    message = get_unlock_message(owned_lock)
    assert '<@foo>' in message
    assert '<@bar>' in message
