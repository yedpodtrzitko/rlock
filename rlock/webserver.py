from typing import Tuple
import json
import arrow
from mach9 import Mach9
from mach9.exceptions import ServerError
from mach9.response import text, json as json_response

from .slackbot import channel_message
from .lock import get_lock, Lock, set_lock, remove_lock, get_lock_subscribers, add_lock_subscriber
from . import config

app = Mach9()

client = config.get_redis()


def get_request_duration(params: list) -> int:
    """
    return timestamp when the lock will expiry
    """
    duration = config.LOCK_DURATION
    try:
        duration = abs(int(params[0]))
    except:
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


def try_respond(lock: Lock, message: str):
    """
    Try to post a message back to the channel.
    If that fails, show message back to the user.
    """
    try:
        success = channel_message(lock, message)
    except:
        success = False

    if not success:
        return json_response({
            'response_type': 'in_channel',
            'text': message,
        })

    return text(None, status=204)


def extract_request(data: dict) -> Tuple[Lock, list]:
    """
    Extract data from the incoming command.
    """
    if data['team_id'][0] != config.SLACK_TEAM:
        raise ServerError('invalid team')

    try:
        params = data['text'][0].split()
    except:
        params = []

    try:
        lock = Lock(
            channel_id=data['channel_id'][0],
            user_id=data['user_id'][0],
            user_name=data['user_name'][0],
            expiry_tstamp=get_request_duration(params),
            channel_notified=0,
            user_notified=0,
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


def do_lock(new_lock: Lock, extra_msg: str = None):
    old_lock = get_lock(new_lock.channel_id)
    if old_lock and not old_lock.is_expired:
        if old_lock.user_id != new_lock.user_id:
            if add_lock_subscriber(old_lock, new_lock.user_id):
                return text('Currently locked, I will ping you when the lock will expire.')
            else:
                return text('Currently locked, ping already planned.')

        if set_lock(new_lock):
            return try_respond(new_lock, f'🔐 _LOCK extended_ {extra_msg or ""}')

    if set_lock(new_lock):
        return try_respond(new_lock, f'🔐 _LOCK_ {extra_msg or ""} ({new_lock.user_name}, {new_lock.duration} mins)')


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

    return try_respond(lock, get_unlock_message(lock))


def get_unlock_message(lock: Lock, extra_msg: str = ''):
    ping_users = get_lock_subscribers(lock)
    slack_names = [f'<@{user}>' for user in ping_users]
    slack_str = slack_names and 'cc ' + ' '.join(slack_names) or ''
    return f'🔓 _unlock_ {extra_msg} {slack_str}'


@app.route('/dialock', methods={'POST'})
async def rdialog(request):
    try:
        payload = json.loads(request.form['payload'][0])
    except:
        return text('failed to parse request')

    if payload['callback_id'] != 'lock_expiry':
        return text('invalid request')

    new_lock = Lock(
        user_id=payload['user']['id'],
        user_name=payload['user']['name'],
        channel_id=payload['original_message']['attachments'][0]['fallback'],
        expiry_tstamp=arrow.now().shift(minutes=+30).timestamp,
        user_notified=0,
        channel_notified=0,
    )

    action = payload['actions'][0]['value']
    if action == 'lock':
        return do_lock(new_lock)

    elif action == 'unlock':
        return do_unlock(new_lock)

    return text('nothing to do')


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=4993, debug=True)
