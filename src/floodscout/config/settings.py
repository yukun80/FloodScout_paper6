from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class ProjectPaths:
    root: Path = field(default_factory=lambda: Path.cwd())
    data_dir: Path = field(init=False)
    state_dir: Path = field(init=False)
    output_dir: Path = field(init=False)

    def __post_init__(self) -> None:
        self.data_dir = self.root / "data"
        self.state_dir = self.data_dir / "state"
        self.output_dir = self.data_dir / "output"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class KeywordConfig:
    flood_terms: tuple[str, ...] = (
        "内涝",
        "积水",
        "道路被淹",
        "地下车库进水",
        "暴雨被困",
        "排水不畅",
    )
    scene_terms: tuple[str, ...] = (
        "路口",
        "小区",
        "地铁站",
        "隧道",
        "主干道",
        "地下通道",
    )


@dataclass(slots=True)
class BatchConfig:
    slice_unit: str = "month"
    max_retries: int = 2
    task_db_name: str = "tasks.db"
    posts_output_name: str = "posts.jsonl"
    events_output_name: str = "events.jsonl"


@dataclass(slots=True)
class CrawlerConfig:
    request_timeout: float = 20.0
    max_pages: int = 3
    sleep_seconds: float = 1.0
    max_retries: int = 3
    retry_backoff_seconds: float = 1.2
    cookie_env_name: str = "WEIBO_COOKIE"
    cookie_file_default: str = "data/input/weibo_cookie.txt"


@dataclass(slots=True)
class AppConfig:
    paths: ProjectPaths = field(default_factory=ProjectPaths)
    keywords: KeywordConfig = field(default_factory=KeywordConfig)
    batch: BatchConfig = field(default_factory=BatchConfig)
    crawler: CrawlerConfig = field(default_factory=CrawlerConfig)
