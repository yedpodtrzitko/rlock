import arrow
import pytest

from ..webserver import Lock
from .. import config

CHANNEL = 'C1Q1NRYKX'
USERID = config.SLACK_TESTUSER


@pytest.fixture
def req_data():
    return {
        'token': ['---'],
        'team_id': [config.SLACK_TEAM],
        'team_domain': ['foobar'],
        'channel_id': [CHANNEL],
        'channel_name': ['dev-null'],
        'user_id': [USERID],
        'user_name': [USERID * 2],
        'command': ['/rlock'],
        'response_url': ['https://vanyli.net'],
        'trigger_id': ['123.123.123'],
        'text': ['30 foo'],
    }


@pytest.fixture
def dialock_data():
    return {
        u'action_ts': u'1519494960.614093',
        u'actions': [
            {
                u'name': u'action', u'type': u'button', u'value': u'unlock'
            }
        ],
        u'attachment_id': u'1',
        u'callback_id': u'lock_expiry',
        u'channel': {
            u'id': u'xxx',
            u'name': u'directmessage',
        },
        u'is_app_unfurl': False,
        u'message_ts': u'123',
        u'original_message': {
            u'attachments': [
                {
                    u'actions': [
                        {
                            u'id': u'1',
                            u'name': u'action',
                            u'style': u'',
                            u'text': u'Remove lock now',
                            u'type': u'button',
                            u'value': u'unlock'},
                        {u'id': u'2',
                         u'name': u'action',
                         u'style': u'',
                         u'text': u'Lock for 30 more minutes',
                         u'type': u'button',
                         u'value': u'lock'},
                        {u'id': u'3',
                         u'name': u'action',
                         u'style': u'',
                         u'text': u'Do nothing',
                         u'type': u'button',
                         u'value': u'nothing'
                         }
                    ],
                    u'callback_id': u'lock_expiry',
                    u'color': u'3AA3E3',
                    u'fallback': CHANNEL,
                    u'id': 1,
                    u'text': u'You can do one of the following actions.'
                }
            ],
            u'bot_id': u'B9DJB0VLZ',
            u'subtype': u'bot_message',
            u'text': f'You lock in <#{CHANNEL}> will expire in about 9',
            u'ts': u'1519494956.000080',
            u'type': u'message',
            u'username': u'ReleaseLock',
        },
        u'response_url': u'http://lolcat.com',
        u'team': {
            u'domain': u'skypicker',
            u'id': config.SLACK_TEAM,
        },
        u'token': u'123123',
        u'trigger_id': u'123.123.123',
        u'type': u'interactive_message',
        u'user': {
            u'id': u'U40L9UPKK',
            u'name': u'yed',
        }
    }


@pytest.fixture
def owned_lock():
    yield Lock(
        user_id=USERID,
        user_name=USERID * 2,
        expiry_tstamp=arrow.now().shift(minutes=+(config.EXPIRY_WARN - 1)).timestamp,
        user_notified=0,
        channel_notified=0,
        channel_id=CHANNEL,
    )


@pytest.fixture
def nonowned_lock():
    yield Lock(
        user_id=USERID * 2,
        user_name=USERID * 2,
        expiry_tstamp=arrow.now().shift(minutes=+(config.EXPIRY_WARN - 1)).timestamp,
        user_notified=0,
        channel_notified=0,
        channel_id=CHANNEL,
    )


@pytest.fixture
def clean_redis():
    redis = config.get_redis()
    redis.flushdb()
    yield redis


@pytest.fixture
def owned_redis(clean_redis, owned_lock: Lock):
    clean_redis.hmset(owned_lock.full_id, owned_lock._asdict())
    yield clean_redis


@pytest.fixture
def nonowned_redis(clean_redis, nonowned_lock: Lock):
    clean_redis.hmset(nonowned_lock.full_id, nonowned_lock._asdict())
    yield clean_redis
