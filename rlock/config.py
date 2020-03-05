from collections import defaultdict

from envparse import env
from redis import StrictRedis
from slackclient import SlackClient
from typing import DefaultDict

SLACK_TEAM = env("SLACK_TEAM", "123123")
SLACK_BOT_TOKEN = env("SLACK_BOT_TOKEN", "")
SLACK_TESTUSER = env("SLACK_TESTUSER", "234234")

LOCK_DURATION = 50  # minutes
REDIS_DB = 3
EXPIRY_WARN = 10  # minutes

CHANNEL_PREFIX = "channel_lock_"  # prefix for redis
CHANNEL_STATS_PREFIX = "channel_stats_"  # prefix for redis
PING_PREFIX = "ping_"
SLACK_TESTS = env("SLACK_TESTS", False)  # if False, tests wont touch Slack

LOCK_ICONS = defaultdict(lambda: "🔐")  # type: DefaultDict

LOCK_ICONS.update({"U666KD6AX": ":tin_thinking:"})  # tin


def get_redis():
    return StrictRedis(db=REDIS_DB)


def get_slackbot():
    return SlackClient(SLACK_BOT_TOKEN)
