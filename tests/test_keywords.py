from floodscout.core.keywords import build_keyword_queries


def test_build_keyword_queries_contains_city_and_terms() -> None:
    queries = build_keyword_queries(
        city="广州",
        flood_terms=("内涝", "积水"),
        scene_terms=("路口",),
    )
    assert "广州 内涝" in queries
    assert "广州 积水 路口" in queries
    assert len(queries) == 4
