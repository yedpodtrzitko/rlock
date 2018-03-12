from typing import NamedTuple, Optional

import arrow
from . import config

client = config.get_redis()


class Lock(NamedTuple):
    user_id: str
    user_name: str
    channel_id: str
    expiry_tstamp: int
    user_notified: int
    channel_notified: int

    @property
    def is_expired(self):
        return self.expiry_tstamp < arrow.now().timestamp

    @property
    def is_expiring(self):
        return self.expiry_tstamp < (arrow.now().timestamp + config.EXPIRY_WARN * 60)

    @property
    def full_id(self):
        return f'{config.CHANNEL_PREFIX}{self.channel_id}'

    @property
    def ping_id(self):
        return f'{config.PING_PREFIX}{self.channel_id}'

    @property
    def duration(self):
        return int((self.expiry_tstamp - arrow.now().timestamp) / 60)


def get_lock(channel_id: str, has_prefix: bool = False) -> Optional[Lock]:
    """
    Check & return owner of a lock in channel.
    """
    key_name = channel_id if has_prefix else f'{config.CHANNEL_PREFIX}{channel_id}'
    fields = Lock._fields
    vals = client.hmget(key_name, fields)
    if not any(vals):
        return None

    values = dict(zip(fields, vals))
    lock = Lock(
        user_id=values['user_id'] and values['user_id'].decode('utf-8'),
        user_name=values['user_name'] and values['user_name'].decode('utf-8'),
        channel_id=values['channel_id'] and values['channel_id'].decode('utf-8'),
        expiry_tstamp=int(values['expiry_tstamp'] or 0),
        user_notified=int(values['user_notified'] or 0),
        channel_notified=int(values['channel_notified'] or 0),
    )

    if lock.is_expired and lock.channel_notified:
        # lock expired & announced, should be gone
        return None

    return lock


def set_lock(lock: Lock) -> bool:
    return client.hmset(lock.full_id, lock._asdict())


def remove_lock(lock: Lock):
    client.hdel(lock.full_id, *lock._fields)


def mark_user_notified(lock: Lock):
    client.hset(lock.full_id, 'user_notified', 1)


def extend_lock(lock: Lock, duration: int):
    new_tstamp = arrow.now().shift(minutes=+duration).timestamp
    client.hset(lock.full_id, 'expiry_tstamp', new_tstamp)


def get_unlock_subscribers(lock: Lock) -> list:
    users = []
    while 1:
        new: bytes = client.spop(lock.ping_id)
        if not new:
            break
        users.append(new.decode('utf-8'))
    return users
