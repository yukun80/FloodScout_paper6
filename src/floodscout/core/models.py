from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class CrawlTask(BaseModel):
    task_id: str
    city: str
    keyword: str
    start_date: str
    end_date: str
    status: TaskStatus = TaskStatus.PENDING
    retries: int = 0


class RawPost(BaseModel):
    platform: str = "weibo"
    post_id: str
    author_id: str | None = None
    author_name: str | None = None
    publish_time_raw: str
    crawl_time: datetime
    text_raw: str
    media_urls: list[str] = Field(default_factory=list)
    repost_count: int = 0
    comment_count: int = 0
    like_count: int = 0
    source_url: str | None = None
    search_keyword: str
    city_hint: str


class NormalizedPost(BaseModel):
    platform: str
    post_id: str
    publish_time: datetime
    text_clean: str
    search_keyword: str
    city_hint: str
    media_urls: list[str]


class ClassifiedPost(BaseModel):
    post: NormalizedPost
    label: str
    score: float
    reason: str


class ExtractedFact(BaseModel):
    post_id: str
    city: str
    district: str | None = None
    event_type: str
    water_depth_cm: int | None = None
    road_blocked: bool = False
    people_trapped: bool = False
    confidence: float
    label: str
    event_time: datetime


class AggregatedEvent(BaseModel):
    event_id: str
    city: str
    date: str
    event_type: str
    evidence_count: int
    median_water_depth_cm: int | None
    event_confidence: float
    post_ids: list[str]
