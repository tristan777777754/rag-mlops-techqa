from scripts.freeze_data002_split import allocate, group_queries


def test_grouping_keeps_transitive_duplicates_and_contexts_together():
    records = [
        {"id": "a", "question": "  SAME Q ", "contexts": []},
        {
            "id": "b",
            "question": "same q",
            "contexts": [{"filename": "b.txt", "text": "body\r\n"}],
        },
        {
            "id": "c",
            "question": "other wording",
            "contexts": [{"filename": "c.txt", "text": "body\n"}],
        },
        {"id": "d", "question": "reviewed wording", "contexts": []},
        {"id": "e", "question": "independent", "contexts": []},
    ]
    review = [
        {"left_id": "c", "right_id": "d", "decision": "merge", "reason": "same issue"}
    ]
    groups = group_queries(records, review)
    assert groups["a"] == groups["b"] == groups["c"] == groups["d"]
    assert groups["e"] != groups["a"]
    assert groups == group_queries(records[::-1], review)
    category = dict.fromkeys(groups, "known_positive")
    splits = allocate(groups, category)
    assert set(splits) == set(groups)
    assert splits["a"] == splits["b"] == splits["c"] == splits["d"]
    assert splits == allocate(dict(reversed(list(groups.items()))), category)
