from time import sleep

import pytest

from ..webserver import try_respond
from .. import config
from ..slackbot import channel_message, user_message
from ..tasker import check_channel_expiration


@pytest.mark.skipif(config.SLACK_TESTS is False, reason="default tests only")
def test_basic_user_message(owned_lock):
    user_message(owned_lock, text="some test message")


@pytest.mark.skipif(config.SLACK_TESTS is False, reason="default tests only")
def test_basic_channel_message(owned_lock):
    channel_message(owned_lock, "🔓 _unlock_ (test)")


@pytest.mark.skipif(config.SLACK_TESTS is False, reason="default tests only")
def test_notify_upcoming_expiration(owned_redis, owned_lock):
    assert owned_lock.is_expiring
    assert not owned_lock.user_notified
    assert not owned_lock.is_expired
    check_channel_expiration(owned_lock)


@pytest.mark.skipif(config.SLACK_TESTS is False, reason="default tests only")
def test_update_message_on_subscribe(owned_lock):
    try_respond(owned_lock, owned_lock.get_lock_message())

    assert owned_lock.message_id

    sleep(1)

    owned_lock.add_new_subscriber("foooooo")

    owned_lock.get_unlock_message()
