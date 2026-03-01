from __future__ import annotations

from floodscout.core.models import AggregatedEvent, CrawlTask, ExtractedFact, NormalizedPost
from floodscout.crawler.base import WeiboCrawler
from floodscout.pipeline.classify import classify_posts
from floodscout.pipeline.cleaning import normalize_posts
from floodscout.pipeline.dedup import deduplicate_posts
from floodscout.pipeline.extract import extract_facts
from floodscout.pipeline.fuse import aggregate_events


class PipelineRunner:
    def __init__(self, crawler: WeiboCrawler) -> None:
        self.crawler = crawler

    def run_task(
        self, task: CrawlTask
    ) -> tuple[list[NormalizedPost], list[ExtractedFact], list[AggregatedEvent]]:
        raw_posts = self.crawler.fetch(task)
        normalized = normalize_posts(raw_posts)
        deduped = deduplicate_posts(normalized)
        classified = classify_posts(deduped)
        facts = extract_facts(classified)
        events = aggregate_events(facts)
        return deduped, facts, events
