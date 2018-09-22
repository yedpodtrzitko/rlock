import json
from typing import Tuple

import arrow
from mach9 import Mach9
from mach9.exceptions import ServerError
from mach9.response import json as json_response, HTTPResponse
from mach9.response import text

from . import config
from .lock import get_lock, Lock, remove_lock, set_lock
from .slackbot import channel_message, react_message

app = Mach9()

client = config.get_redis()


def get_request_duration(params: list) -> int:
    """
    return timestamp when the lock will expiry
    """
    duration = config.LOCK_DURATION
    try:
        duration = abs(int(params[0]))
    except Exception:
        pass

    return arrow.now().shift(minutes=+duration).timestamp


def get_request_message(params: list) -> str:
    """
    Check if there are any extra params sent with the lock and return them eventually.
    """
    if not params:
        return ""

    try:
        int(params[0])
    except ValueError:
        offset = 0  # 1st isnt duration
    else:
        offset = 1  # 1st is duration

    return " ".join(params[offset:])


def try_respond(lock: Lock, message: str, init_lock: bool = False) -> Tuple[HTTPResponse, str]:
    """
    Try to post a message back to the channel.
    If that fails, show message back to the user.
    """
    try:
        success, msg_id = channel_message(lock.channel_id, message, init_lock=init_lock)
    except Exception:
        success, msg_id = False, ""

    if not success:
        return json_response({"response_type": "in_channel", "text": message}), ""
    elif init_lock:
        lock.set_message_id(msg_id)

    return text(None, status=204), msg_id


def extract_request(data: dict) -> Tuple[Lock, list]:
    """
    Extract data from the incoming command.
    """
    if data["team_id"][0] != config.SLACK_TEAM:
        raise ServerError("invalid team")

    try:
        params = data["text"][0].split()
    except Exception:
        params = []

    try:
        lock = Lock(
            channel_id=data["channel_id"][0], user_id=data["user_id"][0], expiry_tstamp=get_request_duration(params)
        )
    except IndexError:
        raise ServerError("invalid request")

    return lock, params


@app.route("/lock", methods={"POST"})
async def rlock(request):
    """
    Attempt to set a lock in channel.
    """
    new_lock, params = extract_request(request.form)
    new_lock.extra_msg = get_request_message(params)
    return do_lock(new_lock)


def do_lock(new_lock: Lock):
    old_lock = get_lock(new_lock.channel_id)
    if old_lock and not old_lock.is_expired:
        if old_lock.user_id != new_lock.user_id:
            if old_lock.add_new_subscriber(new_lock.user_id):
                return text("Currently locked, I will ping you when the lock will expire.")
            else:
                return text("Currently locked & ping planned already.")

        new_lock.expiry_tstamp = get_extension_timestamp(new_lock.channel_id)
        new_lock.message_id = old_lock.message_id
        new_lock.init_tstamp = old_lock.init_tstamp
        new_lock.extra_msg = old_lock.extra_msg
        if set_lock(new_lock):
            new_lock.update_lock_message()
            response, msg_id = try_respond(new_lock, f"🔐 _LOCK extended_")
            if response:
                react_message(new_lock, msg_id, "classic")
            return response

    if set_lock(new_lock):
        return try_respond(new_lock, new_lock.get_lock_message(), init_lock=True)[0]


@app.route("/unlock", methods={"POST"})
async def runlock(request):
    new_lock, params = extract_request(request.form)

    return do_unlock(new_lock)


def do_unlock(lock: Lock):
    old_lock = get_lock(lock.channel_id)
    if not old_lock:
        return text("No lock set")

    if old_lock.user_id != lock.user_id:
        return text(f"Cant unlock, locked by <@{old_lock.user_id}>")

    try:
        old_lock.update_lock_message(unlock=True)
    except Exception:
        pass

    try:
        remove_lock(lock)
    except Exception:
        return text("Failed to unlock, try again")

    return try_respond(lock, lock.get_unlock_message())[0]


@app.route("/dialock", methods={"POST"})
async def rdialog(request):
    try:
        payload = json.loads(request.form["payload"][0])
    except Exception:
        return text("failed to parse request")

    if payload["callback_id"] != "lock_expiry":
        return text("invalid request")

    channel_id = payload["channel"]["id"]
    request_user = payload["user"]["id"]

    new_lock = get_lock(channel_id)
    if not new_lock:
        channel_message(channel_id, "chosen lock is not valid anymore", user=request_user)
        return text(None, status=204)  # no lock exists

    if new_lock.user_id != request_user:
        channel_message(channel_id, "can't interact with non-owned lock", user=request_user)
        return text(None, status=204)  # cant interact with non-owned lock

    action = payload["actions"][0]["value"]
    if action == "lock":
        return do_lock(new_lock)

    elif action == "unlock":
        return do_unlock(new_lock)

    return text("nothing to do")


def get_extension_timestamp(channel_id: str) -> int:
    current_lock = get_lock(channel_id)
    if current_lock:
        planned_expiry = arrow.get(current_lock.expiry_tstamp).shift(minutes=30).timestamp
    else:
        planned_expiry = arrow.now().shift(minutes=+30).timestamp

    return planned_expiry


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=4993, debug=False)
