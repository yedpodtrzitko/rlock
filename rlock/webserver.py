import json
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from typing import Tuple, Optional

import arrow
import uvicorn

from .channel_stats import get_stats
from . import config
from .lock import get_lock, Lock, remove_lock, set_lock
from .slackbot import channel_message, react_message

app = Starlette(debug=False)

client = config.get_redis()


def get_request_duration(params: list) -> int:
    """
    return timestamp when the lock will expiry
    """
    try:
        duration = abs(int(params[0]))
    except Exception:
        duration = config.LOCK_DURATION

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


def try_respond(
    lock: Lock, message: str, init_lock: bool = False
) -> Tuple[Response, str]:
    """
    Try to post a message back to the channel.
    If that fails, show message back to the user.
    """
    try:
        success, msg_id = channel_message(lock.channel_id, message, init_lock=init_lock)
    except Exception:
        success, msg_id = False, ""

    if not success:
        return JSONResponse({"response_type": "in_channel", "text": message}), ""
    elif init_lock:
        lock.set_message_id(msg_id)

    return PlainTextResponse(None, status_code=204), msg_id


def extract_request(data: dict) -> Tuple[Lock, list]:
    """
    Extract data from the incoming command.
    """
    if data["team_id"] != config.SLACK_TEAM:
        raise RuntimeError("invalid team")

    try:
        params = data["text"].split()
    except Exception:
        params = []

    try:
        lock = Lock(
            channel_id=data["channel_id"],
            user_id=data["user_id"],
            expiry_tstamp=get_request_duration(params),
        )
    except IndexError:
        raise RuntimeError("invalid request")

    return lock, params


@app.route("/lock", methods=["POST"])
async def rlock(request: Request):
    """
    Attempt to set a lock in channel.
    """
    form_data = await request.form()
    new_lock, params = extract_request(form_data)
    new_lock.extra_msg = get_request_message(params)
    return do_lock(new_lock)


def do_lock(new_lock: Lock, lock_time: Optional[int] = None):
    old_lock = get_lock(new_lock.channel_id)
    channel_stats = get_stats(new_lock.channel_id)
    if old_lock and not old_lock.is_expired:
        if old_lock.user_id != new_lock.user_id:
            if old_lock.add_new_subscriber(new_lock.user_id):
                return PlainTextResponse(
                    "Currently locked, I will ping you when the lock will expire."
                )
            else:
                return PlainTextResponse("Currently locked & ping planned already.")

        lock_time = lock_time or 30
        new_lock.expiry_tstamp = get_extension_timestamp(old_lock, lock_time)
        new_lock.message_id = old_lock.message_id
        new_lock.init_tstamp = old_lock.init_tstamp
        new_lock.extra_msg = old_lock.extra_msg
        new_lock.user_notified = 0
        if set_lock(new_lock):
            new_lock.update_lock_message()
            response, msg_id = try_respond(
                new_lock, f"🔐 _LOCK extended_ ({lock_time} mins)"
            )
            if msg_id:
                channel_stats.mark_extend(save=True)
                react_message(new_lock, msg_id, "classic")
            return response

    if set_lock(new_lock):
        response, msg = try_respond(
            new_lock, new_lock.get_lock_message(), init_lock=True
        )
        if msg:  # was success
            channel_stats.mark_lock(save=True)
        return response


@app.route("/unlock", methods=["POST"])
async def runlock(request: Request) -> Response:
    form_data = await request.form()
    new_lock, params = extract_request(form_data)

    return do_unlock(new_lock)


def do_unlock(lock: Lock):
    old_lock = get_lock(lock.channel_id)
    if not old_lock:
        return PlainTextResponse("No lock set")

    if old_lock.user_id != lock.user_id:
        return PlainTextResponse(f"Cant unlock, locked by <@{old_lock.user_id}>")

    try:
        old_lock.update_lock_message(unlock=True)
    except Exception:
        pass

    try:
        remove_lock(lock)
    except Exception:
        return PlainTextResponse("Failed to unlock, try again")

    return try_respond(lock, lock.get_unlock_message())[0]


@app.route("/dialock", methods=["POST"])
async def rdialog(request):
    try:
        form_data = await request.form()
        payload = json.loads(form_data["payload"])
    except Exception:
        raise RuntimeError("failed to parse request")

    if payload["callback_id"] != "lock_expiry":
        return PlainTextResponse("invalid request")

    channel_id = payload["channel"]["id"]
    request_user = payload["user"]["id"]

    new_lock = get_lock(channel_id)
    if not new_lock:
        channel_message(
            channel_id, "chosen lock is not valid anymore", user=request_user
        )
        print("first")
        return PlainTextResponse(None, status_code=204)  # no lock exists

    if new_lock.user_id != request_user:
        channel_message(
            channel_id, "can't interact with non-owned lock", user=request_user
        )
        print("second", new_lock.user_id, request_user)
        return PlainTextResponse(
            None, status_code=204
        )  # cant interact with non-owned lock

    action = payload["actions"][0]["value"]
    if action.startswith("lock"):
        try:
            action, _, lock_time = action.partition("_")
            lock_time = int(lock_time)
        except Exception:
            lock_time = None

        return do_lock(new_lock, lock_time)

    elif action == "unlock":
        return do_unlock(new_lock)

    return PlainTextResponse("nothing to do")


@app.exception_handler(500)
async def server_error(request, exc):
    return PlainTextResponse("something went wrong", status_code=500)


def get_extension_timestamp(current_lock: Lock, lock_time: Optional[int] = None) -> int:
    lock_time = lock_time or 30
    if current_lock:
        planned_expiry = (
            arrow.get(current_lock.expiry_tstamp).shift(minutes=lock_time).timestamp
        )
    else:
        planned_expiry = arrow.now().shift(minutes=lock_time).timestamp

    return planned_expiry


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
