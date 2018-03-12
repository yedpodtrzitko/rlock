from redis import StrictRedis
from envparse import env
from slackclient import SlackClient

SLACK_TEAM = env('SLACK_TEAM', '123123')
SLACK_BOT_TOKEN = env('SLACK_BOT_TOKEN')
SLACK_TESTUSER = env('SLACK_TESTUSER', '234234')

LOCK_DURATION = 60  # minutes
REDIS_DB = 3
EXPIRY_WARN = 10  # minutes

CHANNEL_PREFIX = 'channel_'  # prefix for redis
PING_PREFIX = 'ping_'
SLACK_TESTS = env('SLACK_TESTS', False)  # if False, tests wont touch Slack


def get_redis():
    return StrictRedis(db=REDIS_DB)


def get_slackbot():
    return SlackClient(SLACK_BOT_TOKEN)
