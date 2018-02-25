from huey import RedisHuey, crontab

from .lock import get_lock, Lock, remove_lock, mark_user_notified
from . import config
from .slackbot import channel_message, user_message

huey = RedisHuey('rlock', host='localhost')

client = config.get_redis()


@huey.periodic_task(crontab(minute='*'))
def check_expirations():
    keys = client.keys(f'{config.CHANNEL_PREFIX}*')
    for channel in keys:
        lock = get_lock(channel, has_prefix=True)
        check_channel_expiration(lock)


def check_channel_expiration(lock: Lock):
    if not lock:
        return

    if lock.is_expired:
        if not lock.channel_notified:
            channel_message(lock, '🔓 _unlock_ (expired)')

        remove_lock(lock)

    elif lock.is_expiring and not lock.user_notified:
        message_data = {
            'text': f'Your lock in <#{lock.channel_id}> will expire in about {lock.duration} minutes',
            'attachments': [
                {
                    "fallback": lock.channel_id,  # I dont know where to put it
                    "callback_id": "lock_expiry",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    "text": "You can do one of the following actions.",
                    "actions": [
                        {
                            "name": "action",
                            "text": "Remove lock now",
                            "type": "button",
                            "value": "unlock",

                        },
                        {
                            "name": "action",
                            "text": "Lock for 30 more minutes",
                            "type": "button",
                            "value": "lock",
                        },
                        {
                            "name": "action",
                            "text": "Do nothing",
                            "type": "button",
                            "value": "nothing",
                        },
                    ]
                }
            ]
        }

        if user_message(lock, **message_data):
            mark_user_notified(lock)
