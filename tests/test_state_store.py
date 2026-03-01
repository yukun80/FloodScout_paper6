from pathlib import Path

from floodscout.core.models import CrawlTask
from floodscout.storage.state_store import TaskStateStore


def test_task_state_store_lifecycle(tmp_path: Path) -> None:
    db = tmp_path / "tasks.db"
    store = TaskStateStore(db, max_retries=2)
    task = CrawlTask(
        task_id="a",
        city="广州",
        keyword="广州 内涝",
        start_date="2020-01-01",
        end_date="2020-01-31",
    )

    store.upsert_tasks([task])
    pending = store.fetch_pending(limit=10)
    assert len(pending) == 1

    store.mark_running("a")
    store.mark_done("a")

    summary = store.summary()
    assert summary["done"] == 1
