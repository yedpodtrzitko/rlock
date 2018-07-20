import json
from typing import Tuple

import arrow
from mach9 import Mach9
from mach9.exceptions import ServerError
from mach9.response import json as json_response
from mach9.response import text

from . import config
from .lock import get_lock, Lock, remove_lock, set_lock
from .slackbot import channel_message

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
        return ''

    try:
        int(params[0])
    except ValueError:
        offset = 0  # 1st isnt duration
    else:
        offset = 1  # 1st is duration

    return ' '.join(params[offset:])


def try_respond(lock: Lock, message: str, init_lock: bool = False):
    """
    Try to post a message back to the channel.
    If that fails, show message back to the user.
    """
    try:
        success, msg_id = channel_message(lock, message)
    except Exception:
        success, msg_id = False, ''

    if not success:
        return json_response({
            'response_type': 'in_channel',
            'text': message,
        })
    elif init_lock:
        lock.set_message_id(msg_id)

    return text(None, status=204)


def extract_request(data: dict) -> Tuple[Lock, list]:
    """
    Extract data from the incoming command.
    """
    if data['team_id'][0] != config.SLACK_TEAM:
        raise ServerError('invalid team')

    try:
        params = data['text'][0].split()
    except Exception:
        params = []

    try:
        lock = Lock(
            channel_id=data['channel_id'][0],
            user_id=data['user_id'][0],
            user_name=data['user_name'][0],
            expiry_tstamp=get_request_duration(params),
        )
    except IndexError:
        raise ServerError('invalid request')

    return lock, params


@app.route('/lock', methods={'POST'})
async def rlock(request):
    """
    Attempt to set a lock in channel.
    """
    new_lock, params = extract_request(request.form)
    extra_msg = get_request_message(params)

    return do_lock(new_lock, extra_msg)


def do_lock(new_lock: Lock, extra_msg: str = ''):
    old_lock = get_lock(new_lock.channel_id)
    if old_lock and not old_lock.is_expired:
        if old_lock.user_id != new_lock.user_id:
            if old_lock.add_new_subscriber(new_lock.user_id):
                return text('Currently locked, I will ping you when the lock will expire.')
            else:
                return text('Currently locked & ping planned already.')

        new_lock.expiry_tstamp = get_extension_timestamp(new_lock.channel_id)
        new_lock.message_id = old_lock.message_id
        new_lock.init_tstamp = old_lock.init_tstamp
        if set_lock(new_lock):
            new_lock.update_lock_message()
            return try_respond(new_lock, f'🔐 _LOCK extended_ {extra_msg or ""}')

    if set_lock(new_lock):
        return try_respond(new_lock, new_lock.get_lock_message(extra_msg), init_lock=True)


@app.route('/unlock', methods={'POST'})
async def runlock(request):
    new_lock, params = extract_request(request.form)

    return do_unlock(new_lock)


def do_unlock(lock: Lock):
    old_lock = get_lock(lock.channel_id)
    if not old_lock:
        return text('No lock set')

    if old_lock.user_id != lock.user_id:
        return text(f'Cant unlock, locked by <@{old_lock.user_id}>')

    try:
        remove_lock(lock)
    except:
        return text('Failed to unlock, try again')

    return try_respond(lock, lock.get_unlock_message())


@app.route('/dialock', methods={'POST'})
async def rdialog(request):
    try:
        payload = json.loads(request.form['payload'][0])
    except:
        return text('failed to parse request')

    if payload['callback_id'] != 'lock_expiry':
        return text('invalid request')

    channel_id = payload['original_message']['attachments'][0]['fallback']
    new_lock = Lock(
        user_id=payload['user']['id'],
        user_name=payload['user']['name'],
        channel_id=channel_id,
        expiry_tstamp=get_extension_timestamp(channel_id),
    )

    action = payload['actions'][0]['value']
    if action == 'lock':
        return do_lock(new_lock)

    elif action == 'unlock':
        return do_unlock(new_lock)

    return text('nothing to do')


def get_extension_timestamp(channel_id: str) -> int:
    current_lock = get_lock(channel_id)
    if current_lock:
        planned_expiry = arrow.get(current_lock.expiry_tstamp).shift(minutes=30).timestamp
    else:
        planned_expiry = arrow.now().shift(minutes=+30).timestamp

    return planned_expiry


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4993, debug=False)
