import arrow
from attr import asdict
import pytest

from .. import config
from ..webserver import Lock

CHANNEL = "C1Q1NRYKX"
USERID = config.SLACK_TESTUSER
OTHER_USERID = USERID * 2
SET_EXPIRY = arrow.now().shift(minutes=(config.EXPIRY_WARN - 1)).timestamp


@pytest.fixture
def req_data():
    return {
        "token": ["---"],
        "team_id": [config.SLACK_TEAM],
        "team_domain": ["foobar"],
        "channel_id": [CHANNEL],
        "channel_name": ["dev-null"],
        "user_id": [USERID],
        "command": ["/rlock"],
        "response_url": ["https://vanyli.net"],
        "trigger_id": ["123.123.123"],
        "text": ["30 foo"],
    }


@pytest.fixture
def dialock_data():
    return {
        "action_ts": "1519494960.614093",
        "actions": [{"name": "action", "type": "button", "value": "unlock"}],
        "attachment_id": "1",
        "callback_id": "lock_expiry",
        "channel": {"id": "xxx", "name": "directmessage"},
        "is_app_unfurl": False,
        "message_ts": "123",
        "original_message": {
            "attachments": [
                {
                    "actions": [
                        {
                            "id": "1",
                            "name": "action",
                            "style": "",
                            "text": "Remove lock now",
                            "type": "button",
                            "value": "unlock",
                        },
                        {
                            "id": "2",
                            "name": "action",
                            "style": "",
                            "text": "Lock for 30 more minutes",
                            "type": "button",
                            "value": "lock",
                        },
                        {
                            "id": "3",
                            "name": "action",
                            "style": "",
                            "text": "Do nothing",
                            "type": "button",
                            "value": "nothing",
                        },
                    ],
                    "callback_id": "lock_expiry",
                    "color": "3AA3E3",
                    "fallback": CHANNEL,
                    "id": 1,
                    "text": "You can do one of the following actions.",
                }
            ],
            "bot_id": "B9DJB0VLZ",
            "subtype": "bot_message",
            "text": f"You lock in <#{CHANNEL}> will expire in about 9",
            "ts": "1519494956.000080",
            "type": "message",
            "username": "ReleaseLock",
        },
        "response_url": "http://lolcat.com",
        "team": {"domain": "skypicker", "id": config.SLACK_TEAM},
        "token": "123123",
        "trigger_id": "123.123.123",
        "type": "interactive_message",
        "user": {"id": "U40L9UPKK", "name": "yed"},
    }


@pytest.fixture
def owned_lock():
    yield Lock(user_id=USERID, expiry_tstamp=SET_EXPIRY, channel_id=CHANNEL)


@pytest.fixture
def nonowned_lock():
    yield Lock(user_id=OTHER_USERID, expiry_tstamp=SET_EXPIRY, channel_id=CHANNEL)


@pytest.fixture
def clean_redis():
    redis = config.get_redis()
    redis.flushdb()
    yield redis


@pytest.fixture
def owned_redis(clean_redis, owned_lock: Lock):
    clean_redis.hmset(owned_lock.full_id, asdict(owned_lock))
    yield clean_redis


@pytest.fixture
def nonowned_redis(clean_redis, nonowned_lock: Lock):
    clean_redis.hmset(nonowned_lock.full_id, asdict(nonowned_lock))
    yield clean_redis
