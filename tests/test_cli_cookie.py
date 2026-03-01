import os
from pathlib import Path

import pytest

from floodscout.cli import _resolve_cookie, _validate_cookie_text


def test_resolve_cookie_from_file(tmp_path: Path) -> None:
    cookie_file = tmp_path / "cookie.txt"
    cookie_file.write_text("SUB=abc; SUBP=def;", encoding="utf-8")

    cookie = _resolve_cookie(str(cookie_file), "WEIBO_COOKIE", required=True)
    assert "SUB=abc" in cookie


def test_resolve_cookie_from_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cookie_file = tmp_path / "not_exists.txt"
    monkeypatch.setenv("WEIBO_COOKIE", "SUB=xyz; SUBP=qwe;")

    cookie = _resolve_cookie(str(cookie_file), "WEIBO_COOKIE", required=True)
    assert cookie == "SUB=xyz; SUBP=qwe;"


def test_resolve_cookie_missing(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        _resolve_cookie(str(tmp_path / "missing.txt"), "NO_SUCH_COOKIE_ENV", required=True)


def test_validate_cookie_text_bad() -> None:
    with pytest.raises(ValueError):
        _validate_cookie_text("invalid_cookie")
