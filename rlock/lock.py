from typing import Optional, Tuple

import arrow
import attr
from attr import asdict

from . import config

client = config.get_redis()

LOCK_FIELDS = [
    "user_id",
    "channel_id",
    "expiry_tstamp",
    "user_notified",
    "channel_notified",
    "message_id",
    "extra_msg",
    "init_tstamp",
]


@attr.s
class Lock:
    user_id: str = attr.ib()
    channel_id: str = attr.ib()
    expiry_tstamp: int = attr.ib(default=0)
    init_tstamp: int = attr.ib(factory=lambda: arrow.now().timestamp)
    user_notified: int = attr.ib(default=0)
    channel_notified: int = attr.ib(default=0)
    message_id: Optional[str] = attr.ib(default=None)
    extra_msg: Optional[str] = attr.ib(default=None)

    @property
    def remaining(self) -> int:
        return int((self.expiry_tstamp - arrow.now().timestamp) / 60)

    @property
    def is_expired(self):
        return self.expiry_tstamp < arrow.now().timestamp

    @property
    def is_expiring(self):
        return self.expiry_tstamp < (arrow.now().timestamp + config.EXPIRY_WARN * 60)

    @property
    def full_id(self):
        return f"{config.CHANNEL_PREFIX}{self.channel_id}"

    @property
    def ping_id(self):
        return f"{config.PING_PREFIX}{self.channel_id}"

    @property
    def duration(self):
        return int((self.expiry_tstamp - self.init_tstamp) / 60)

    def set_message_id(self, message_id: str):
        self.message_id = message_id
        client.hset(self.full_id, "message_id", message_id)

    def get_subscribers(self, destructive: bool = False) -> list:
        if not destructive:
            users = client.smembers(self.ping_id)
            return ["`<@{}>`".format(x.decode("utf-8")) for x in users]

        users = []
        while 1:
            new: bytes = client.spop(self.ping_id)
            if not new:
                break
            users.append(new)

        return ["<@{}>".format(x.decode("utf-8")) for x in users]

    def get_unlock_message(self, extra_msg: str = ""):
        subscribers = self.get_subscribers(destructive=True)
        slack_str = "" if not subscribers else " ".join(["\ncc"] + subscribers)
        return f"🔓 _unlock_ {extra_msg} {slack_str}"

    def get_lock_message(self) -> str:
        slack_str = "" if not self.get_subscribers() else " ".join(["\nQ:"] + self.get_subscribers())
        return f'{config.LOCK_ICONS[self.user_id]} _LOCK_ {self.extra_msg or ""} (`<@{self.user_id}>`, {self.duration} mins) {slack_str}'

    def update_lock_message(self, unlock: bool = False) -> Tuple[bool, Optional[str]]:
        from .slackbot import update_channel_message

        return update_channel_message(self, self.get_lock_message(), unlock=unlock)

    def add_new_subscriber(self, ping_user: str) -> int:
        new_sub = client.sadd(self.ping_id, ping_user)
        if new_sub:
            self.update_lock_message()

        return new_sub


def get_lock(channel_id: str, has_prefix: bool = False) -> Optional[Lock]:
    """
    Check & return owner of a lock in channel.
    """
    key_name = channel_id if has_prefix else f"{config.CHANNEL_PREFIX}{channel_id}"
    vals = client.hmget(key_name, LOCK_FIELDS)
    if not any(vals):
        return None

    values = dict(zip(LOCK_FIELDS, vals))
    lock = Lock(
        user_id=values["user_id"] and values["user_id"].decode("utf-8"),
        channel_id=values["channel_id"] and values["channel_id"].decode("utf-8"),
        expiry_tstamp=int(values["expiry_tstamp"]),
        init_tstamp=int(values.get("init_tstamp") or arrow.now().timestamp),
        user_notified=int(values["user_notified"] or 0),
        channel_notified=int(values["channel_notified"] or 0),
        message_id=values.get("message_id") and values["message_id"].decode("utf-8"),
        extra_msg=values.get("extra_msg") and values["extra_msg"].decode("utf-8"),
    )

    if lock.is_expired and lock.channel_notified:
        # lock expired & announced, should be gone
        return None

    return lock


def set_lock(lock: Lock) -> bool:
    return client.hmset(lock.full_id, asdict(lock))


def remove_lock(lock: Lock):
    client.hdel(lock.full_id, *LOCK_FIELDS)


def mark_user_notified(lock: Lock):
    client.hset(lock.full_id, "user_notified", 1)
