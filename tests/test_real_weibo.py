from datetime import datetime, timedelta, timezone

from floodscout.crawler.real_weibo import (
    RealWeiboCrawler,
    _extract_mblogs,
    clean_weibo_html,
    extract_media_urls,
    parse_weibo_created_at,
)


def test_clean_weibo_html() -> None:
    text = clean_weibo_html("<a href='/'>广州</a> 积水&nbsp;严重")
    assert text == "广州 积水 严重"


def test_parse_weibo_created_at_relative() -> None:
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone(timedelta(hours=8)))
    parsed = parse_weibo_created_at("5分钟前", now=now)
    assert parsed == now - timedelta(minutes=5)


def test_extract_mblogs_from_cards_and_groups() -> None:
    payload = {
        "data": {
            "cards": [
                {"mblog": {"id": "1", "text": "a"}},
                {"card_group": [{"mblog": {"id": "2", "text": "b"}}]},
            ]
        }
    }
    items = _extract_mblogs(payload)
    assert [item["id"] for item in items] == ["1", "2"]


def test_extract_media_urls() -> None:
    mblog = {
        "pics": [{"large": {"url": "https://img/1.jpg"}}, {"url": "https://img/2.jpg"}],
        "page_info": {"page_pic": {"url": "https://img/3.jpg"}},
    }
    urls = extract_media_urls(mblog)
    assert len(urls) == 3


def test_build_headers_keyword_referer_is_urlencoded_ascii() -> None:
    crawler = RealWeiboCrawler()
    headers = crawler._build_headers(keyword="宝鸡 内涝")
    referer = headers["Referer"]
    assert "宝鸡" not in referer
    assert "q%3D" in referer
    # "宝鸡 内涝" encoded by quote_plus: %E5%AE%9D%E9%B8%A1+%E5%86%85%E6%B6%9D
    assert "%E5%AE%9D%E9%B8%A1" in referer
