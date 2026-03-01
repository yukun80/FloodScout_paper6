from floodscout.core.models import CrawlTask
from floodscout.crawler.mock_weibo import MockWeiboCrawler
from floodscout.pipeline.runner import PipelineRunner


def test_pipeline_runner_outputs_events() -> None:
    task = CrawlTask(
        task_id="t1",
        city="广州",
        keyword="广州 内涝",
        start_date="2020-01-01",
        end_date="2020-01-31",
    )
    runner = PipelineRunner(crawler=MockWeiboCrawler())
    posts, facts, events = runner.run_task(task)

    assert len(posts) >= 1
    assert len(facts) >= 1
    assert len(events) >= 1
