from .conftest import CHANNEL, OTHER_USERID, SET_EXPIRY, USERID

from ..channel_stats import get_stats, save_stats


def test_marking():
    stats = get_stats(CHANNEL)

    assert not stats.locks_count

    assert stats.is_today

    assert not stats.locks_count
    stats.mark_lock()
    assert stats.locks_count == 1

    assert not stats.extends_count
    stats.mark_extend()
    assert stats.extends_count == 1


def test_date_match():
    stats = get_stats(CHANNEL)
    stats.created_tstamp -= 3600 * 24
    assert not stats.is_today
    stats.locks_count = 10
    save_stats(stats)

    stats = get_stats(CHANNEL)
    assert stats.is_today
    assert not stats.locks_count
