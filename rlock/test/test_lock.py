import json

import arrow
import pytest

from .. import slackbot, tasker, webserver
from ..lock import get_lock
from .conftest import CHANNEL, OTHER_USERID, SET_EXPIRY, USERID


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    monkeypatch.setattr(
        webserver, "channel_message", lambda *args, **kwargs: (True, 123)
    )
    monkeypatch.setattr(
        slackbot, "channel_message", lambda *args, **kwargs: (True, 123)
    )
    monkeypatch.setattr(tasker, "channel_message", lambda *args, **kwargs: (True, 123))


def test_obtain_lock(test_client, req_data, clean_redis):
    response = test_client.post("/lock", data=req_data)
    assert response.status_code == 204
    assert get_lock(CHANNEL).user_id == USERID


def test_extend_lock(test_client, owned_redis, req_data):
    lock = get_lock(CHANNEL)
    assert lock.expiry_tstamp == SET_EXPIRY

    response = test_client.post("/lock", data=req_data)
    assert response.status_code == 204
    lock = get_lock(CHANNEL)
    assert lock.user_id == USERID
    assert lock.expiry_tstamp == SET_EXPIRY + (30 * 60)


def test_unlock(test_client, owned_redis, req_data):
    response = test_client.post("/unlock", data=req_data)
    assert response.status_code == 204
    assert not get_lock(CHANNEL)


def test_lock_nonowned(test_client, nonowned_redis, req_data):
    response = test_client.post("/lock", data=req_data)
    assert (
        response.text == "Currently locked, I will ping you when the lock will expire."
    )

    lock = get_lock(CHANNEL)
    assert lock.user_id == OTHER_USERID
    assert lock.get_subscribers() == ["`<@{}>`".format(USERID)]


def test_unlock_nonowned(test_client, nonowned_redis, req_data):
    response = test_client.post("/unlock", data=req_data)
    assert response.text.startswith("Cant unlock, locked by ")


def test_overwrite_expired_lock(test_client, clean_redis, req_data):
    clean_redis.hmset(
        f"channel_{CHANNEL}",
        {
            "user_id": OTHER_USERID,
            "expiry_tstamp": arrow.now().shift(minutes=-1).timestamp,
        },
    )

    response = test_client.post("/lock", data=req_data)
    assert response.status_code == 204
    assert get_lock(CHANNEL).user_id == USERID


def test_dialock_unlock(test_client, owned_redis, dialock_data):
    req_data = {"payload": [json.dumps(dialock_data)]}

    response = test_client.post("/dialock", data=req_data)
    assert response.status_code == 204
    assert get_lock(CHANNEL) is None


def test_dialock_extend(test_client, owned_redis, dialock_data):
    dialock_data["actions"][0]["value"] = "lock"
    req_data = {"payload": [json.dumps(dialock_data)]}

    lock = get_lock(CHANNEL)
    assert lock.expiry_tstamp == SET_EXPIRY
    assert lock.is_expiring

    response = test_client.post("/dialock", data=req_data)
    assert response.status_code == 204

    lock = get_lock(CHANNEL)
    assert not lock.user_notified
    assert not lock.is_expiring
    assert lock.expiry_tstamp == SET_EXPIRY + (30 * 60)


def test_dialock_nonowned_unlock(test_client, nonowned_redis, dialock_data):
    req_data = {"payload": [json.dumps(dialock_data)]}

    response = test_client.post("/dialock", data=req_data)
    assert response.status_code == 204
    assert not response.text
    assert get_lock(CHANNEL)


def test_get_unlock_message(owned_redis, owned_lock):
    owned_lock.add_new_subscriber("foo")
    owned_lock.add_new_subscriber("bar")
    message = owned_lock.get_unlock_message()
    assert "<@foo>" in message
    assert "<@bar>" in message
