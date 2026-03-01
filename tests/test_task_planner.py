from datetime import date

from floodscout.core.task_planner import build_time_slices, TaskPlanner


def test_build_time_slices_month() -> None:
    slices = build_time_slices(date(2020, 1, 15), date(2020, 3, 2), "month")
    assert len(slices) == 3
    assert slices[0].start_date.isoformat() == "2020-01-15"
    assert slices[2].end_date.isoformat() == "2020-03-02"


def test_task_planner_builds_tasks() -> None:
    planner = TaskPlanner(flood_terms=("内涝",), scene_terms=("路口",))
    tasks = planner.build_tasks(
        cities=["广州"],
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 31),
        slice_unit="month",
    )
    assert len(tasks) == 2
    assert tasks[0].city == "广州"
