from datetime import datetime, timedelta, timezone

from floodscout.crawler.real_weibo import parse_weibo_created_at


def test_parse_weibo_created_at_yesterday() -> None:
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    parsed = parse_weibo_created_at("昨天 10:30", now=now)
    assert parsed.day == 28
    assert parsed.hour == 10
    assert parsed.minute == 30


def test_parse_weibo_created_at_cn_month_day() -> None:
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    parsed = parse_weibo_created_at("2月18日 09:20", now=now)
    assert parsed.month == 2
    assert parsed.day == 18
    assert parsed.hour == 9
    assert parsed.minute == 20
