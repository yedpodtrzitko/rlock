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
        "type": "interactive_message",
        "actions": [{"name": "action", "type": "button", "value": "unlock"}],
        "callback_id": "lock_expiry",
        "team": {"id": config.SLACK_TEAM, "domain": "xxx"},
        "channel": {"id": "C1Q1NRYKX", "name": "dev-null"},
        "user": {"id": "U40L9UPKK", "name": "yed"},
        "action_ts": "1537589980.308553",
        "message_ts": "1537589969.000100",
        "attachment_id": "1",
        "token": "xxx",
        "is_app_unfurl": False,
        "original_message": {
            "text": ":closed_lock_with_key: _LOCK_  (`<@U40L9UPKK>`, 50 mins) ",
            "username": "ReleaseLock",
            "bot_id": "B9DJB0VLZ",
            "attachments": [
                {
                    "callback_id": "lock_expiry",
                    "fallback": "buttons for /rlock /runlock actions",
                    "id": 1,
                    "actions": [
                        {
                            "id": "1",
                            "name": "lock",
                            "text": "Extend",
                            "type": "button",
                            "value": "lock",
                            "style": "",
                        },
                        {
                            "id": "2",
                            "name": "unlock",
                            "text": "Unlock",
                            "type": "button",
                            "value": "unlock",
                            "style": "",
                        },
                    ],
                }
            ],
            "type": "message",
            "subtype": "bot_message",
            "ts": "1537589969.000100",
        },
        "response_url": "https://hooks.slack.com/actions/XXX/YYY/ZZZ",
        "trigger_id": "442287622246.2169119100.XXX",
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
