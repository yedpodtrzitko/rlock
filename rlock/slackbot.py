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


def channel_message(
    channel_id: str, message: str, init_lock: bool = False, user: Optional[str] = None
) -> Tuple[bool, str]:

    if init_lock:
        attachments: Optional[list] = [
            {
                "fallback": "buttons for /rlock /runlock actions",
                "callback_id": "lock_expiry",
                "actions": [
                    {"name": "lock", "text": "Extend", "type": "button", "value": "lock"},
                    {"name": "unlock", "text": "Unlock", "type": "button", "value": "unlock"},
                ],
            }
        ]
    else:
        attachments = None

    if user:
        res = bot.api_call(
            "chat.postEphemeral", token=bot.token, channel=channel_id, text=message, attachments=attachments, user=user
        )
    else:
        res = bot.api_call(
            "chat.postMessage", token=bot.token, channel=channel_id, text=message, attachments=attachments
        )

    return res["ok"], res.get("ts", "")


def update_channel_message(lock: Lock, message: str, unlock: bool = False) -> Tuple[bool, Optional[str]]:
    if unlock:
        res = bot.api_call("chat.update", token=bot.token, channel=lock.channel_id, text=message, ts=lock.message_id,
                           attachments=[])
    else:
        res = bot.api_call("chat.update", token=bot.token, channel=lock.channel_id, text=message, ts=lock.message_id)

    return res["ok"], lock.message_id
