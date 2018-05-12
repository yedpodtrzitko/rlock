from .lock import Lock
from . import config

bot = config.get_slackbot()


def user_message(lock: Lock, **message_data) -> bool:
    res_json = bot.api_call(
        'im.open',
        token=bot.token,
        user=lock.user_id,
    )

    if not res_json['ok']:
        return False

    channel = res_json['channel']['id']

    res = bot.api_call(
        'chat.postMessage',
        token=bot.token,
        channel=channel,
        **message_data,
    )
    return res['ok']


def channel_message(lock: Lock, message: str) -> bool:
    res = bot.api_call(
        'chat.postMessage',
        token=bot.token,
        channel=lock.channel_id,
        text=message,
    )
    return res['ok']
