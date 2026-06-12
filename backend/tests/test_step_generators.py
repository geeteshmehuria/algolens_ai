from app.services.step_generators import (
    binary_search_steps,
    two_pointers_pair_sum_steps,
    two_pointers_palindrome_steps,
    stack_bracket_steps,
    generate_for_problem,
    _parse_example_input,
)


# --- input parsing ---


def test_parse_array_and_target():
    parsed = _parse_example_input("nums = [2,7,11,15], target = 9")
    assert parsed["array"] == [2, 7, 11, 15]
    assert parsed["target"] == 9


def test_parse_string():
    parsed = _parse_example_input('s = "A man, a plan"')
    assert parsed["string"] == "A man, a plan"


# --- binary search ---


def test_binary_search_finds_target():
    result = binary_search_steps([-1, 0, 3, 5, 9, 12], 9)
    assert result["animation_type"] == "binary_search"
    final = result["steps"][-1]
    assert final["found"] == result["input"]["array"].index(9)


def test_binary_search_not_found_ends_without_found():
    result = binary_search_steps([1, 3, 5], 4)
    final = result["steps"][-1]
    assert final["found"] is None
    assert "not in the array" in final["result"]


def test_binary_search_steps_have_valid_indices():
    result = binary_search_steps([1, 2, 3, 4, 5, 6, 7, 8], 7)
    n = len(result["input"]["array"])
    for step in result["steps"]:
        if step["mid"] is not None:
            assert 0 <= step["mid"] < n
        for idx in step["eliminated"]:
            assert 0 <= idx < n


# --- two pointers ---


def test_pair_sum_found_pair_adds_to_target():
    result = two_pointers_pair_sum_steps([1, 3, 4, 6, 8], 10)
    final = result["steps"][-1]
    arr = result["input"]["array"]
    assert final["found"] is not None
    i, j = final["found"]
    assert arr[i] + arr[j] == 10


def test_pair_sum_no_pair():
    result = two_pointers_pair_sum_steps([1, 2, 3], 100)
    assert result["steps"][-1]["found"] is None


def test_palindrome_detects_true_and_false():
    assert (
        "IS a palindrome"
        in two_pointers_palindrome_steps("racecar")["steps"][-1]["result"]
    )
    assert "false" in two_pointers_palindrome_steps("abc")["steps"][-1]["result"]


def test_palindrome_strips_non_alphanumeric():
    result = two_pointers_palindrome_steps("A man, a plan")
    assert all(c.isalnum() for c in result["input"]["array"])


# --- stack ---


def test_stack_valid_brackets():
    result = stack_bracket_steps("([])")
    assert "VALID" in result["steps"][-1]["result"]
    assert result["steps"][-1]["stack"] == []


def test_stack_invalid_brackets_stop_early():
    result = stack_bracket_steps("(]")
    assert "INVALID" in result["steps"][-1]["result"]


def test_stack_unclosed_brackets_invalid():
    result = stack_bracket_steps("((")
    assert "INVALID" in result["steps"][-1]["result"]


def test_stack_ops_are_consistent():
    result = stack_bracket_steps("{[()]}")
    for step in result["steps"]:
        assert step["op"] in ("push", "pop", "skip")
        assert isinstance(step["stack"], list)


# --- pattern dispatch ---


def test_generate_for_problem_dispatches_by_pattern(session, make_problem):
    bs = make_problem(
        title="Binary Search",
        topic="Binary Search",
        pattern="Binary Search",
        examples=[{"input": "nums = [-1,0,3,5,9,12], target = 9", "output": "4"}],
    )
    result = generate_for_problem(bs, "Binary Search", "Binary Search")
    assert result["animation_type"] == "binary_search"
    assert result["input"]["target"] == 9


def test_generate_for_problem_palindrome_uses_string(session, make_problem):
    p = make_problem(
        title="Valid Palindrome",
        topic="Two Pointers",
        pattern="Two Pointers",
        description="check if it is a palindrome",
        examples=[{"input": 's = "racecar"', "output": "true"}],
    )
    result = generate_for_problem(p, "Two Pointers", "Two Pointers")
    assert result["animation_type"] == "two_pointers"
    assert result["input"]["array"] == list("racecar")


def test_generate_for_problem_unsupported_pattern_returns_none(session, make_problem):
    p = make_problem(title="House Robber", topic="Dynamic Programming", pattern="1D DP")
    assert generate_for_problem(p, "Dynamic Programming", "1D DP") is None
