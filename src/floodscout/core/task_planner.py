from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from calendar import monthrange

from floodscout.core.keywords import build_keyword_queries
from floodscout.core.models import CrawlTask


@dataclass(slots=True)
class TimeSlice:
    start_date: date
    end_date: date


class TaskPlanner:
    def __init__(self, flood_terms: tuple[str, ...], scene_terms: tuple[str, ...]) -> None:
        self._flood_terms = flood_terms
        self._scene_terms = scene_terms

    def build_tasks(
        self,
        cities: list[str],
        start_date: date,
        end_date: date,
        slice_unit: str,
    ) -> list[CrawlTask]:
        slices = build_time_slices(start_date, end_date, slice_unit)
        tasks: list[CrawlTask] = []
        for city in cities:
            keywords = build_keyword_queries(city, self._flood_terms, self._scene_terms)
            for keyword in keywords:
                for s in slices:
                    task_id = f"{city}|{keyword}|{s.start_date}|{s.end_date}"
                    tasks.append(
                        CrawlTask(
                            task_id=task_id,
                            city=city,
                            keyword=keyword,
                            start_date=s.start_date.isoformat(),
                            end_date=s.end_date.isoformat(),
                        )
                    )
        return tasks


def build_time_slices(start_date: date, end_date: date, slice_unit: str) -> list[TimeSlice]:
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")

    if slice_unit == "week":
        return _build_week_slices(start_date, end_date)
    if slice_unit == "month":
        return _build_month_slices(start_date, end_date)
    raise ValueError("slice_unit must be one of: week, month")


def _build_week_slices(start_date: date, end_date: date) -> list[TimeSlice]:
    slices: list[TimeSlice] = []
    cursor = start_date
    while cursor <= end_date:
        current_end = min(end_date, cursor.fromordinal(cursor.toordinal() + 6))
        slices.append(TimeSlice(start_date=cursor, end_date=current_end))
        cursor = current_end.fromordinal(current_end.toordinal() + 1)
    return slices


def _build_month_slices(start_date: date, end_date: date) -> list[TimeSlice]:
    slices: list[TimeSlice] = []
    year, month = start_date.year, start_date.month
    while True:
        last_day = monthrange(year, month)[1]
        month_start = date(year, month, 1)
        month_end = date(year, month, last_day)
        current_start = max(start_date, month_start)
        current_end = min(end_date, month_end)
        if current_start <= current_end:
            slices.append(TimeSlice(start_date=current_start, end_date=current_end))

        if month_end >= end_date:
            break

        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return slices
