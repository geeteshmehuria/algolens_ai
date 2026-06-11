# app/services/step_generators.py
"""Deterministic animation step generators.

Real algorithm implementations instrumented to emit visualization steps that
follow the same JSON contracts as the AI animations (ai_service.ANIMATION_CONTRACTS).
Preferred over Gemini whenever the problem's pattern maps to a supported
generator: the steps are exact by construction, cost zero tokens, and work
without an API key. Inputs are parsed from the problem's first example when
possible, with sensible defaults otherwise.
"""
import re
from typing import Any, Dict, List, Optional

from app.models import DSAProblem
from app.services.ai_service import pick_animation_type

MAX_ELEMENTS = 10  # keep visuals readable


def _parse_example_input(text: str) -> Dict[str, Any]:
    """Best-effort extraction of array / target / string from an example input
    like: nums = [2,7,11,15], target = 9  or  s = "A man, a plan" """
    out: Dict[str, Any] = {}
    m = re.search(r"\[([-\d,\s]+)\]", text)
    if m:
        try:
            out["array"] = [int(x) for x in m.group(1).split(",") if x.strip()]
        except ValueError:
            pass
    m = re.search(r"target\s*=\s*(-?\d+)", text)
    if m:
        out["target"] = int(m.group(1))
    m = re.search(r'"([^"]+)"', text)
    if m:
        out["string"] = m.group(1)
    return out


def binary_search_steps(array: List[int], target: int) -> Dict[str, Any]:
    array = sorted(array)[:MAX_ELEMENTS]
    low, high = 0, len(array) - 1
    eliminated: List[int] = []
    steps = [{
        "low": low, "high": high, "mid": None, "eliminated": [], "found": None,
        "action": f"Search the whole array for target {target}.",
        "result": f"low=0, high={high} — {len(array)} candidates.",
    }]
    while low <= high:
        mid = (low + high) // 2
        if array[mid] == target:
            steps.append({
                "low": low, "high": high, "mid": mid, "eliminated": eliminated[:], "found": mid,
                "action": f"mid={mid}: arr[{mid}]={array[mid]} equals the target.",
                "result": f"Found target at index {mid}!",
            })
            break
        if array[mid] < target:
            eliminated.extend(range(low, mid + 1))
            steps.append({
                "low": mid + 1, "high": high, "mid": mid, "eliminated": eliminated[:], "found": None,
                "action": f"mid={mid}: arr[{mid}]={array[mid]} < {target}.",
                "result": f"Discard indices {low}..{mid} — the answer can only be to the right.",
            })
            low = mid + 1
        else:
            eliminated.extend(range(mid, high + 1))
            steps.append({
                "low": low, "high": mid - 1, "mid": mid, "eliminated": eliminated[:], "found": None,
                "action": f"mid={mid}: arr[{mid}]={array[mid]} > {target}.",
                "result": f"Discard indices {mid}..{high} — the answer can only be to the left.",
            })
            high = mid - 1
    else:
        steps.append({
            "low": low, "high": high, "mid": None, "eliminated": eliminated[:], "found": None,
            "action": "low has crossed high — the search space is empty.",
            "result": f"Target {target} is not in the array. Return -1.",
        })
    return {"animation_type": "binary_search", "input": {"array": array, "target": target}, "steps": steps}


def two_pointers_pair_sum_steps(array: List[int], target: int) -> Dict[str, Any]:
    arr = sorted(array)[:MAX_ELEMENTS]
    left, right = 0, len(arr) - 1
    steps = [{
        "left": left, "right": right, "found": None,
        "action": "Start with pointers at both ends of the sorted array.",
        "result": f"{arr[left]} + {arr[right]} = {arr[left] + arr[right]} (target {target}).",
    }]
    found = False
    while left < right:
        s = arr[left] + arr[right]
        if s == target:
            steps.append({
                "left": left, "right": right, "found": [left, right],
                "action": f"{arr[left]} + {arr[right]} = {s} equals the target.",
                "result": f"Pair found at indices [{left}, {right}]!",
            })
            found = True
            break
        if s < target:
            left += 1
            steps.append({
                "left": left, "right": right, "found": None,
                "action": f"Sum {s} < {target} — only moving the LEFT pointer can increase the sum.",
                "result": f"Move left to index {left} ({arr[left]}).",
            })
        else:
            right -= 1
            steps.append({
                "left": left, "right": right, "found": None,
                "action": f"Sum {s} > {target} — only moving the RIGHT pointer can decrease the sum.",
                "result": f"Move right to index {right} ({arr[right]}).",
            })
    if not found:
        steps.append({
            "left": left, "right": right, "found": None,
            "action": "Pointers have met — every pair has been considered.",
            "result": "No pair adds up to the target.",
        })
    return {"animation_type": "two_pointers", "input": {"array": arr}, "steps": steps}


def two_pointers_palindrome_steps(s: str) -> Dict[str, Any]:
    chars = [c.lower() for c in s if c.isalnum()][:12] or list("racecar")
    left, right = 0, len(chars) - 1
    steps = []
    is_palindrome = True
    while left < right:
        match = chars[left] == chars[right]
        steps.append({
            "left": left, "right": right, "found": [left, right] if match else None,
            "action": f"Compare '{chars[left]}' (index {left}) with '{chars[right]}' (index {right}).",
            "result": "They match — move both pointers inward." if match
                      else "Mismatch — this is NOT a palindrome.",
        })
        if not match:
            is_palindrome = False
            break
        left += 1
        right -= 1
    steps.append({
        "left": left, "right": right, "found": None,
        "action": "Pointers have met or crossed." if is_palindrome else "Comparison stopped at the mismatch.",
        "result": "Every pair matched — it IS a palindrome!" if is_palindrome
                  else "Return false.",
    })
    return {"animation_type": "two_pointers", "input": {"array": chars}, "steps": steps}


_BRACKET_PAIRS = {")": "(", "]": "[", "}": "{"}


def stack_bracket_steps(s: str) -> Dict[str, Any]:
    chars = [c for c in s if c in "()[]{}"][:12] or list("([])")
    stack: List[str] = []
    steps: List[Dict[str, Any]] = []
    valid = True
    for i, ch in enumerate(chars):
        if ch in "([{":
            stack.append(ch)
            steps.append({
                "cursor": i, "op": "push", "value": ch, "stack": stack[:],
                "action": f"'{ch}' is an opening bracket.",
                "result": f"Push '{ch}' onto the stack.",
            })
        elif stack and stack[-1] == _BRACKET_PAIRS[ch]:
            top = stack.pop()
            steps.append({
                "cursor": i, "op": "pop", "value": top, "stack": stack[:],
                "action": f"'{ch}' closes the most recent opener '{top}'.",
                "result": f"Matched — pop '{top}'.",
            })
        else:
            expected = stack[-1] if stack else "nothing"
            steps.append({
                "cursor": i, "op": "skip", "value": ch, "stack": stack[:],
                "action": f"'{ch}' arrived but the stack top is '{expected}'.",
                "result": "No match — the sequence is INVALID.",
            })
            valid = False
            break
    if valid:
        steps.append({
            "cursor": len(chars) - 1, "op": "skip", "value": "", "stack": stack[:],
            "action": "All characters processed.",
            "result": "Stack is empty — the sequence is VALID!" if not stack
                      else f"Stack still holds {stack} — unclosed brackets, INVALID.",
        })
    return {"animation_type": "stack", "input": {"array": chars}, "steps": steps}


def generate_for_problem(
    problem: DSAProblem, topic_name: str = "", pattern_name: str = ""
) -> Optional[Dict[str, Any]]:
    """Return a deterministic animation for the problem, or None when its
    pattern has no generator (caller falls back to Gemini)."""
    anim_type = pick_animation_type(pattern_name, topic_name)
    example_input = ""
    if problem.examples:
        example_input = str(problem.examples[0].get("input", ""))
    parsed = _parse_example_input(example_input)
    text = f"{problem.title} {problem.description}".lower()

    if anim_type == "binary_search":
        array = parsed.get("array") or [-1, 0, 3, 5, 9, 12]
        target = parsed.get("target")
        if target is None:
            target = sorted(array)[len(array) // 2]
        return binary_search_steps(array, target)

    if anim_type == "two_pointers":
        if "palindrome" in text:
            return two_pointers_palindrome_steps(parsed.get("string") or "racecar")
        array = parsed.get("array") or [1, 3, 4, 6, 8]
        target = parsed.get("target")
        if target is None:
            ordered = sorted(array)
            target = ordered[0] + ordered[-1]
        return two_pointers_pair_sum_steps(array, target)

    if anim_type == "stack":
        return stack_bracket_steps(parsed.get("string") or "([])")

    return None
