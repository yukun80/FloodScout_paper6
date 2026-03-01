from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from pydantic import BaseModel


class JsonlOutputStore:
    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, items: Iterable[BaseModel]) -> int:
        count = 0
        with self.file_path.open("a", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item.model_dump(mode="json"), ensure_ascii=False))
                f.write("\n")
                count += 1
        return count
