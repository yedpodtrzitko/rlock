from datetime import date

import arrow
from typing import Tuple

import attr

from .slackbot import channel_message
from . import config

client = config.get_redis()

STATS_FIELDS = [
    "channel_id",
    "created_tstamp",
    "locks_count",
    "extends_count",
    "lock_minutes",
    "longest_lock",
]


@attr.s
class ChannelStats:
    channel_id: str = attr.ib()
    created_tstamp: int = attr.ib()
    locks_count: int = attr.ib()
    extends_count: int = attr.ib()
    lock_minutes: int = attr.ib()
    longest_lock: int = attr.ib()

    @property
    def full_id(self):
        return f"{config.CHANNEL_STATS_PREFIX}{self.channel_id}"

    def mark_extend(self, save=False) -> None:
        self.extends_count += 1
        if save:
            save_stats(self)

    def mark_lock(self, save=False) -> None:
        self.locks_count += 1
        if save:
            save_stats(self)

    @property
    def is_today(self) -> bool:
        record = arrow.get(self.created_tstamp)
        return record.date() == date.today()


def get_stats(channel_id: str) -> ChannelStats:
    key_name = f"{config.CHANNEL_STATS_PREFIX}{channel_id}"
    vals = client.hmget(key_name, STATS_FIELDS)
    stats = None
    if any(vals):
        values = dict(zip(STATS_FIELDS, vals))
        stats = ChannelStats(
            channel_id=values["channel_id"] and values["channel_id"].decode("utf-8"),
            created_tstamp=int(values["created_tstamp"]) or 0,
            locks_count=int(values["locks_count"]) or 0,
            extends_count=int(values["extends_count"]) or 0,
            lock_minutes=int(values["lock_minutes"]) or 0,
            longest_lock=int(values["longest_lock"]) or 0,
        )

        if not stats.is_today:
            remove_stats(stats)
            stats = None

    if not stats:
        stats = ChannelStats(
            channel_id=channel_id,
            created_tstamp=arrow.now().timestamp,
            locks_count=0,
            extends_count=0,
            lock_minutes=0,
            longest_lock=0,
        )

    return stats


def print_stats(stats: ChannelStats) -> Tuple[bool, str]:
    message = "\n".join(
        [
            "Hello yes, see today stats:",
            f"number of locks: {stats.locks_count}",
            f"number of lock extends: {stats.extends_count}",
        ]
    )
    return channel_message(stats.channel_id, message)


def remove_stats(stats: ChannelStats):
    client.hdel(stats.full_id, *STATS_FIELDS)


def save_stats(stats: ChannelStats) -> bool:
    return client.hmset(stats.full_id, attr.asdict(stats))
