from huey import crontab, RedisHuey

from . import config
from .lock import get_lock, Lock, mark_user_notified, remove_lock
from .slackbot import channel_message

huey = RedisHuey("rlock", host="localhost")

client = config.get_redis()


@huey.periodic_task(crontab(minute="*"))
def check_expirations():
    keys = client.keys(f"{config.CHANNEL_PREFIX}*")
    for channel in keys:
        lock = get_lock(channel, has_prefix=True)
        check_channel_expiration(lock)


def check_channel_expiration(lock: Lock):
    if not lock:
        return

    if lock.is_expired:
        if not lock.channel_notified:
            lock.update_lock_message(unlock=True)
            channel_message(lock.channel_id, lock.get_unlock_message("(expired)"))

        remove_lock(lock)

    elif lock.is_expiring and not lock.user_notified:
        message = f"<@{lock.user_id}>, your lock will expire in about {lock.remaining} minutes."
        if channel_message(lock.channel_id, message=message, user=lock.user_id):
            mark_user_notified(lock)
