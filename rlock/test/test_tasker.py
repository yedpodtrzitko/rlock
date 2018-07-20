import pytest

from .. import lock, slackbot, tasker, webserver


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    monkeypatch.setattr(webserver, "channel_message", lambda *args, **kwargs: (True, 123))
    monkeypatch.setattr(slackbot, "channel_message", lambda *args, **kwargs: (True, 123))
    monkeypatch.setattr(tasker, "channel_message", lambda *args, **kwargs: (True, 123))


def test_notify_upcoming_expiration(owned_redis, owned_lock, mocker):
    mock_notify_upcoming_expiration = mocker.patch.object(tasker, 'user_message')

    assert owned_lock.is_expiring
    assert not owned_lock.user_notified

    tasker.check_channel_expiration(owned_lock)

    assert mock_notify_upcoming_expiration.called


def test_notify_expired(owned_redis, owned_lock, mocker):
    mock_notify_upcoming_expiration = mocker.patch.object(tasker, 'user_message')
    mock_notify_expired = mocker.patch.object(tasker, 'channel_message')

    owned_redis.hset(owned_lock.full_id, 'user_notified', 1)
    owned_redis.hset(owned_lock.full_id, 'expiry_tstamp', 123)

    updated_lock = lock.get_lock(owned_lock.full_id, True)

    assert updated_lock.user_notified
    assert not updated_lock.channel_notified

    tasker.check_channel_expiration(updated_lock)

    assert not mock_notify_upcoming_expiration.called
    assert mock_notify_expired.called
    assert not owned_redis.hget(owned_lock.full_id, 'user_notified')


def test_dont_notify(owned_redis, owned_lock, mocker):
    mock_notify_upcoming_expiration = mocker.patch.object(tasker, 'user_message')
    mock_notify_expired = mocker.patch.object(tasker, 'channel_message')
    mock_remove_lock = mocker.patch.object(lock, 'remove_lock')

    owned_redis.hset(owned_lock.full_id, 'expiry_tstamp', owned_lock.expiry_tstamp + 3600)

    updated_lock = lock.get_lock(owned_lock.full_id, True)

    tasker.check_channel_expiration(updated_lock)

    assert not mock_notify_upcoming_expiration.called
    assert not mock_notify_expired.called
    assert not mock_remove_lock.called
