from __future__ import annotations

from itertools import product


def build_keyword_queries(
    city: str,
    flood_terms: tuple[str, ...],
    scene_terms: tuple[str, ...],
) -> list[str]:
    """Generate stable city-scoped keyword queries."""
    queries = {f"{city} {flood}" for flood in flood_terms}
    for flood, scene in product(flood_terms, scene_terms):
        queries.add(f"{city} {flood} {scene}")
    return sorted(queries)
