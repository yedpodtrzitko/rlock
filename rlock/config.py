from collections import defaultdict

from envparse import env
from redis import StrictRedis
from slackclient import SlackClient
from typing import DefaultDict

SLACK_TEAM = env("SLACK_TEAM", "team")
SLACK_BOT_TOKEN = env("SLACK_BOT_TOKEN", "token")
SLACK_TESTUSER = env("SLACK_TESTUSER", "U40L9UPKK")

REDIS_DB = env("REDIS_DB", "redis://redis/0")
LOCK_DURATION = 50  # minutes
EXPIRY_WARN = 10  # minutes

CHANNEL_PREFIX = "channel_lock_"  # prefix for redis
CHANNEL_STATS_PREFIX = "channel_stats_"  # prefix for redis
PING_PREFIX = "ping_"
SLACK_TESTS = env("SLACK_TESTS", False)  # if False, tests wont touch Slack

LOCK_ICONS = defaultdict(lambda: "🔐")  # type: DefaultDict

LOCK_ICONS.update({"U666KD6AX": ":tin_thinking:"})  # tin


def get_redis():
    return StrictRedis.from_url(REDIS_DB)


def get_slackbot():
    return SlackClient(SLACK_BOT_TOKEN)
