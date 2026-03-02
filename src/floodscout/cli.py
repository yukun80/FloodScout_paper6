from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

from floodscout.analysis import (
    build_review_samples,
    evaluate_keywords,
    write_keyword_metrics_csv,
    write_review_csv,
)
from floodscout.config.settings import AppConfig
from floodscout.core.task_planner import TaskPlanner
from floodscout.crawler import (
    Crawl4AIWeiboCrawler,
    Crawl4AIWeiboCrawlerConfig,
    CrawlBackendRouter,
    MockWeiboCrawler,
    RealWeiboCrawler,
    RealWeiboCrawlerConfig,
)
from floodscout.crawler.base import WeiboCrawler
from floodscout.pipeline.geocode import GaodeGeocoder, GeocodeCache, GeoCoder
from floodscout.pipeline.runner import PipelineRunner
from floodscout.serving import export_events_geojson, run_event_api
from floodscout.storage.output_store import JsonlOutputStore
from floodscout.storage.state_store import TaskStateStore
from floodscout.utils import load_nonempty_lines


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _default_output_file(config: AppConfig, file_name: str) -> str:
    return str(config.paths.output_dir / file_name)


def build_parser() -> argparse.ArgumentParser:
    config = AppConfig()

    parser = argparse.ArgumentParser(prog="floodscout")
    sub = parser.add_subparsers(dest="command", required=True)

    build_tasks = sub.add_parser("build-tasks", help="Generate historical crawl tasks")
    _add_task_source_args(build_tasks)
    build_tasks.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    build_tasks.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    build_tasks.add_argument("--slice-unit", choices=["week", "month"], default="month")

    run_batch = sub.add_parser("run-batch", help="Execute pending tasks")
    run_batch.add_argument("--limit", type=int, default=50, help="How many tasks to process")
    _add_crawler_args(run_batch, config)

    crawl_history = sub.add_parser(
        "crawl-history",
        help="Build tasks and run real-time Weibo crawling in one command",
    )
    _add_task_source_args(crawl_history)
    crawl_history.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    crawl_history.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    crawl_history.add_argument("--slice-unit", choices=["week", "month"], default="month")
    crawl_history.add_argument("--limit", type=int, default=200, help="How many tasks to process")
    _add_crawler_args(crawl_history, config)

    check_cookie = sub.add_parser("check-weibo-cookie", help="Validate Weibo cookie before crawling")
    check_cookie.add_argument(
        "--weibo-cookie-file",
        default=config.crawler.cookie_file_default,
        help="Cookie file for real Weibo crawler",
    )
    check_cookie.add_argument(
        "--weibo-cookie-env",
        default=config.crawler.cookie_env_name,
        help="Environment variable name for cookie fallback",
    )
    check_cookie.add_argument(
        "--request-timeout",
        type=float,
        default=config.crawler.request_timeout,
        help="HTTP request timeout seconds",
    )

    eval_keywords = sub.add_parser(
        "evaluate-keywords", help="Evaluate keyword quality from processed outputs"
    )
    eval_keywords.add_argument(
        "--posts-file",
        default=_default_output_file(config, config.batch.posts_output_name),
        help="Normalized posts JSONL file",
    )
    eval_keywords.add_argument(
        "--facts-file",
        default=_default_output_file(config, "facts.jsonl"),
        help="Extracted facts JSONL file",
    )
    eval_keywords.add_argument(
        "--output-file",
        default=_default_output_file(config, "keyword_metrics.csv"),
        help="Keyword evaluation CSV output",
    )

    sample_review = sub.add_parser(
        "sample-review", help="Create manual review samples from processed outputs"
    )
    sample_review.add_argument(
        "--posts-file",
        default=_default_output_file(config, config.batch.posts_output_name),
        help="Normalized posts JSONL file",
    )
    sample_review.add_argument(
        "--facts-file",
        default=_default_output_file(config, "facts.jsonl"),
        help="Extracted facts JSONL file",
    )
    sample_review.add_argument(
        "--output-file",
        default=_default_output_file(config, "review_samples.csv"),
        help="Manual review CSV output",
    )
    sample_review.add_argument("--sample-size", type=int, default=200)
    sample_review.add_argument("--seed", type=int, default=42)

    serve = sub.add_parser("serve-events", help="Serve event query HTTP API")
    serve.add_argument(
        "--events-file",
        default=_default_output_file(config, config.batch.events_output_name),
        help="Events JSONL file",
    )
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    export_geojson = sub.add_parser("export-geojson", help="Export events as GeoJSON")
    export_geojson.add_argument(
        "--events-file",
        default=_default_output_file(config, config.batch.events_output_name),
        help="Events JSONL file",
    )
    export_geojson.add_argument(
        "--output-file",
        default=_default_output_file(config, "events.geojson"),
        help="GeoJSON output file",
    )

    return parser


def _add_task_source_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cities", nargs="+", default=[], help="City names")
    parser.add_argument("--cities-file", help="Path to city list file")
    parser.add_argument("--flood-terms-file", help="Path to flood terms file")
    parser.add_argument("--scene-terms-file", help="Path to scene terms file")


def _add_crawler_args(parser: argparse.ArgumentParser, config: AppConfig) -> None:
    parser.add_argument(
        "--crawler",
        choices=["weibo", "mock"],
        default="weibo",
        help="Crawler backend. Default is real weibo crawler.",
    )
    parser.add_argument(
        "--crawler-mode",
        choices=["api", "hybrid", "crawl4ai"],
        default="hybrid",
        help="Crawler routing mode when crawler=weibo.",
    )
    parser.add_argument(
        "--weibo-cookie-file",
        default=config.crawler.cookie_file_default,
        help="Cookie file for real Weibo crawler",
    )
    parser.add_argument(
        "--weibo-cookie-env",
        default=config.crawler.cookie_env_name,
        help="Environment variable name for cookie fallback",
    )
    parser.add_argument(
        "--skip-cookie-check",
        action="store_true",
        help="Skip online cookie validation before crawling",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=config.crawler.max_pages,
        help="Max pages per task for real crawler",
    )
    parser.add_argument(
        "--request-timeout",
        type=float,
        default=config.crawler.request_timeout,
        help="HTTP request timeout seconds for real crawler",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=config.crawler.sleep_seconds,
        help="Sleep seconds between pages for real crawler",
    )
    parser.add_argument(
        "--request-retries",
        type=int,
        default=config.crawler.max_retries,
        help="Retry count per HTTP request for real crawler",
    )
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        default=config.crawler.retry_backoff_seconds,
        help="Retry backoff base seconds for real crawler",
    )
    parser.add_argument(
        "--crawl4ai-headless",
        action="store_true",
        default=config.crawl4ai.headless,
        help="Run Crawl4AI in headless mode.",
    )
    parser.add_argument(
        "--crawl4ai-timeout-ms",
        type=int,
        default=config.crawl4ai.page_timeout_ms,
        help="Crawl4AI page timeout in milliseconds.",
    )
    parser.add_argument(
        "--enable-geocode",
        action="store_true",
        default=config.geo.enabled,
        help="Enable geocoding for extracted location text.",
    )
    parser.add_argument(
        "--geocode-provider",
        choices=["gaode"],
        default=config.geo.provider,
        help="Geocoding provider.",
    )
    parser.add_argument(
        "--gaode-key-env",
        default=config.geo.gaode_key_env_name,
        help="Environment variable name for AMap/高德 API key.",
    )
    parser.add_argument(
        "--geocode-timeout",
        type=float,
        default=config.geo.request_timeout,
        help="Geocoding request timeout seconds.",
    )


def _resolve_cities(args: argparse.Namespace) -> list[str]:
    cities = list(args.cities)
    if args.cities_file:
        cities.extend(load_nonempty_lines(Path(args.cities_file)))
    cities = sorted(set(cities))
    if not cities:
        raise ValueError("At least one city is required. Use --cities or --cities-file.")
    return cities


def _resolve_terms(args: argparse.Namespace, config: AppConfig) -> tuple[tuple[str, ...], tuple[str, ...]]:
    flood_terms = config.keywords.flood_terms
    scene_terms = config.keywords.scene_terms
    if args.flood_terms_file:
        flood_terms = tuple(load_nonempty_lines(Path(args.flood_terms_file)))
    if args.scene_terms_file:
        scene_terms = tuple(load_nonempty_lines(Path(args.scene_terms_file)))
    return flood_terms, scene_terms


def cmd_build_tasks(args: argparse.Namespace, config: AppConfig) -> int:
    cities = _resolve_cities(args)
    flood_terms, scene_terms = _resolve_terms(args, config)

    planner = TaskPlanner(
        flood_terms=flood_terms,
        scene_terms=scene_terms,
    )
    tasks = planner.build_tasks(
        cities=cities,
        start_date=_parse_date(args.start_date),
        end_date=_parse_date(args.end_date),
        slice_unit=args.slice_unit,
    )

    task_db = config.paths.state_dir / config.batch.task_db_name
    store = TaskStateStore(task_db, max_retries=config.batch.max_retries)
    count = store.upsert_tasks(tasks)
    print(f"Created or updated {count} tasks")
    print(f"Task summary: {store.summary()}")
    return 0


def cmd_run_batch(args: argparse.Namespace, config: AppConfig) -> int:
    task_db = config.paths.state_dir / config.batch.task_db_name
    store = TaskStateStore(task_db, max_retries=config.batch.max_retries)

    runner = PipelineRunner(
        crawler=_build_crawler(args, config),
        geocoder=_build_geocoder(args, config),
    )
    return _execute_pending_tasks(args=args, store=store, runner=runner, config=config)


def cmd_crawl_history(args: argparse.Namespace, config: AppConfig) -> int:
    cmd_build_tasks(args, config)

    task_db = config.paths.state_dir / config.batch.task_db_name
    store = TaskStateStore(task_db, max_retries=config.batch.max_retries)

    runner = PipelineRunner(
        crawler=_build_crawler(args, config),
        geocoder=_build_geocoder(args, config),
    )
    return _execute_pending_tasks(args=args, store=store, runner=runner, config=config)


def _execute_pending_tasks(
    args: argparse.Namespace,
    store: TaskStateStore,
    runner: PipelineRunner,
    config: AppConfig,
) -> int:
    posts_store = JsonlOutputStore(config.paths.output_dir / config.batch.posts_output_name)
    facts_store = JsonlOutputStore(config.paths.output_dir / "facts.jsonl")
    events_store = JsonlOutputStore(config.paths.output_dir / config.batch.events_output_name)

    pending = store.fetch_pending(args.limit)
    if not pending:
        print("No pending tasks")
        return 0

    for task in pending:
        try:
            store.mark_running(task.task_id)
            posts, facts, events = runner.run_task(task)
            posts_store.append(posts)
            facts_store.append(facts)
            events_store.append(events)
            store.mark_done(task.task_id)
            print(
                f"DONE task={task.task_id} posts={len(posts)} facts={len(facts)} events={len(events)}"
            )
        except Exception as exc:  # noqa: BLE001
            store.mark_failed(task.task_id, str(exc))
            print(f"FAILED task={task.task_id} error={exc}")

    print(f"Task summary: {store.summary()}")
    return 0


def _build_crawler(args: argparse.Namespace, config: AppConfig) -> WeiboCrawler:
    if args.crawler == "mock":
        return MockWeiboCrawler()

    cookie = _resolve_cookie(
        cookie_file=args.weibo_cookie_file,
        cookie_env=args.weibo_cookie_env,
        required=True,
    )
    cfg = RealWeiboCrawlerConfig(
        request_timeout=args.request_timeout,
        max_pages=args.max_pages,
        sleep_seconds=args.sleep_seconds,
        max_retries=args.request_retries,
        retry_backoff_seconds=args.retry_backoff_seconds,
        cookie=cookie,
    )
    api_crawler = RealWeiboCrawler(config=cfg)
    browser_crawler = Crawl4AIWeiboCrawler(
        config=Crawl4AIWeiboCrawlerConfig(
            cookie=cookie,
            headless=args.crawl4ai_headless,
            page_timeout_ms=args.crawl4ai_timeout_ms,
        )
    )
    mode = args.crawler_mode

    if mode in {"api", "hybrid"} and not args.skip_cookie_check:
        ok, msg = api_crawler.validate_cookie()
        if not ok:
            raise ValueError(f"Weibo cookie invalid: {msg}")
        print(f"Cookie check passed: {msg}")

    if mode == "api":
        return api_crawler
    if mode == "crawl4ai":
        return browser_crawler
    return CrawlBackendRouter(api_crawler=api_crawler, browser_crawler=browser_crawler, mode=mode)


def _build_geocoder(args: argparse.Namespace, config: AppConfig) -> GeoCoder | None:
    if not args.enable_geocode:
        return None
    if args.geocode_provider != "gaode":
        raise ValueError(f"Unsupported geocode provider: {args.geocode_provider}")
    api_key = os.getenv(args.gaode_key_env, "").strip()
    if not api_key:
        raise ValueError(f"Geocode enabled but API key missing. Set env {args.gaode_key_env}.")
    cache = GeocodeCache(config.paths.state_dir / config.geo.cache_db_name)
    return GaodeGeocoder(api_key=api_key, timeout_seconds=args.geocode_timeout, cache=cache)


def _resolve_cookie(cookie_file: str, cookie_env: str, required: bool) -> str | None:
    path = Path(cookie_file)
    if path.exists():
        cookie = path.read_text(encoding="utf-8").strip()
        if cookie:
            _validate_cookie_text(cookie)
            return cookie

    cookie = os.getenv(cookie_env, "").strip()
    if cookie:
        _validate_cookie_text(cookie)
        return cookie

    if required:
        raise ValueError(
            f"Weibo cookie not found. Provide --weibo-cookie-file or set env {cookie_env}."
        )
    return None


def _validate_cookie_text(cookie: str) -> None:
    if "=" not in cookie or ";" not in cookie:
        raise ValueError("Cookie format seems invalid. Expect full request Cookie header string.")


def cmd_check_weibo_cookie(args: argparse.Namespace) -> int:
    cookie = _resolve_cookie(
        cookie_file=args.weibo_cookie_file,
        cookie_env=args.weibo_cookie_env,
        required=True,
    )
    crawler = RealWeiboCrawler(
        config=RealWeiboCrawlerConfig(
            request_timeout=args.request_timeout,
            cookie=cookie,
            max_pages=1,
        )
    )
    ok, msg = crawler.validate_cookie()
    if ok:
        print(f"Cookie check passed: {msg}")
        return 0

    print(f"Cookie check failed: {msg}")
    return 1


def cmd_evaluate_keywords(args: argparse.Namespace) -> int:
    posts_file = Path(args.posts_file)
    facts_file = Path(args.facts_file)
    output_file = Path(args.output_file)

    metrics = evaluate_keywords(posts_file=posts_file, facts_file=facts_file)
    write_keyword_metrics_csv(metrics, output_file)
    print(f"Wrote keyword metrics: {output_file}")
    print(f"Keyword count: {len(metrics)}")
    return 0


def cmd_sample_review(args: argparse.Namespace) -> int:
    samples = build_review_samples(
        posts_file=Path(args.posts_file),
        facts_file=Path(args.facts_file),
        sample_size=args.sample_size,
        seed=args.seed,
    )
    write_review_csv(samples, Path(args.output_file))
    print(f"Wrote review samples: {args.output_file}")
    print(f"Sample count: {len(samples)}")
    return 0


def cmd_serve_events(args: argparse.Namespace) -> int:
    run_event_api(host=args.host, port=args.port, events_file=args.events_file)
    return 0


def cmd_export_geojson(args: argparse.Namespace) -> int:
    count = export_events_geojson(
        events_file=Path(args.events_file),
        output_file=Path(args.output_file),
    )
    print(f"Wrote GeoJSON features: {count} -> {args.output_file}")
    return 0


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = AppConfig()

    try:
        if args.command == "build-tasks":
            return cmd_build_tasks(args, config)
        if args.command == "run-batch":
            return cmd_run_batch(args, config)
        if args.command == "crawl-history":
            return cmd_crawl_history(args, config)
        if args.command == "check-weibo-cookie":
            return cmd_check_weibo_cookie(args)
        if args.command == "evaluate-keywords":
            return cmd_evaluate_keywords(args)
        if args.command == "sample-review":
            return cmd_sample_review(args)
        if args.command == "serve-events":
            return cmd_serve_events(args)
        if args.command == "export-geojson":
            return cmd_export_geojson(args)
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    parser.error("Unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
