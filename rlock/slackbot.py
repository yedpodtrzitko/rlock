from typing import Optional, Tuple

from . import config
from .lock import Lock

bot = config.get_slackbot()


def user_message(lock: Lock, **message_data) -> bool:
    res_json = bot.api_call("im.open", token=bot.token, user=lock.user_id)

    if not res_json["ok"]:
        return False

    channel = res_json["channel"]["id"]

    res = bot.api_call("chat.postMessage", token=bot.token, channel=channel, **message_data)
    return res["ok"]


def react_message(lock: Lock, message_id: str, reaction: str) -> bool:
    try:
        res = bot.api_call(
            "reactions.add", token=bot.token, channel=lock.channel_id, name=reaction, timestamp=message_id
        )
    except Exception:
        return False

    return res["ok"]


def channel_message(lock: Lock, message: str) -> Tuple[bool, str]:
    res = bot.api_call("chat.postMessage", token=bot.token, channel=lock.channel_id, text=message)

    return res["ok"], res["ts"]


def update_channel_message(lock: Lock, message: str) -> Tuple[bool, Optional[str]]:
    res = bot.api_call("chat.update", token=bot.token, channel=lock.channel_id, text=message, ts=lock.message_id)

    return res["ok"], lock.message_id
