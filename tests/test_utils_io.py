from pathlib import Path

from floodscout.utils import load_nonempty_lines


def test_load_nonempty_lines(tmp_path: Path) -> None:
    p = tmp_path / "cities.txt"
    p.write_text("# comment\n\n广州\n 深圳 \n", encoding="utf-8")
    assert load_nonempty_lines(p) == ["广州", "深圳"]
