import urllib.request
import urllib.error
import json
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:8000"

def make_request(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            body = response.read().decode("utf-8")
            return status, json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            error_detail = json.loads(body)
        except Exception:
            error_detail = body
        return e.code, error_detail
    except Exception as e:
        return 0, str(e)

def run_tests():
    print("=== STARTING FULL API INTEGRATION TESTS ===")
    
    # Test 1: Root endpoint
    print("\n[Test 1] GET /")
    status, res = make_request("/")
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 2: User registration
    ts = int(time.time())
    email = f"testuser_{ts}@example.com"
    password = "testpassword123"
    fullname = f"Test User {ts}"
    
    print(f"\n[Test 2] POST /api/auth/register (email: {email})")
    status, res = make_request("/api/auth/register", method="POST", data={
        "email": email,
        "password": password,
        "full_name": fullname
    })
    print(f"Status: {status}, Response: {res}")
    assert status == 201, f"Expected 201, got {status}"
    assert res.get("email") == email
    
    # Test 3: User login
    print("\n[Test 3] POST /api/auth/login")
    status, res = make_request("/api/auth/login", method="POST", data={
        "email": email,
        "password": password
    })
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    token = res.get("access_token")
    assert token is not None, "Login did not return access token"
    
    # Test 4: Get Profile /me
    print("\n[Test 4] GET /api/auth/me")
    status, res = make_request("/api/auth/me", token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    assert res.get("email") == email
    
    # Test 5: Get Topics
    print("\n[Test 5] GET /api/topics")
    status, res = make_request("/api/topics", token=token)
    print(f"Status: {status}, Topics count: {len(res) if isinstance(res, list) else 'N/A'}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 6: Get Patterns
    print("\n[Test 6] GET /api/patterns")
    status, res = make_request("/api/patterns", token=token)
    print(f"Status: {status}, Patterns count: {len(res) if isinstance(res, list) else 'N/A'}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 7: Create a problem
    print("\n[Test 7] POST /api/problems")
    problem_data = {
        "title": f"Custom Test Problem {ts}",
        "difficulty": "Easy",
        "topic_id": 1,
        "pattern_id": 1,
        "description": "Given an array of integers nums, return whether any duplicate exists.",
        "starter_code": "def solve(nums):\n    pass"
    }
    status, res = make_request("/api/problems", method="POST", data=problem_data, token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 201, f"Expected 201, got {status}"
    problem_id = res.get("id")
    assert problem_id is not None
    
    # Test 8: Get all active problems
    print("\n[Test 8] GET /api/problems")
    status, res = make_request("/api/problems", token=token)
    print(f"Status: {status}, Problems count: {len(res) if isinstance(res, list) else 'N/A'}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 9: Get details of the created problem
    print(f"\n[Test 9] GET /api/problems/{problem_id}")
    status, res = make_request(f"/api/problems/{problem_id}", token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 10: Create an attempt
    print(f"\n[Test 10] POST /api/problems/{problem_id}/attempts")
    status, res = make_request(f"/api/problems/{problem_id}/attempts", method="POST", data={
        "submitted_code": "def solve(nums):\n    return len(nums) != len(set(nums))",
        "status": "Correct",
        "used_hint": False,
        "time_complexity": "O(N)",
        "space_complexity": "O(N)"
    }, token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 201, f"Expected 201, got {status}"
    
    # Test 11: Get attempts for the problem
    print(f"\n[Test 11] GET /api/problems/{problem_id}/attempts")
    status, res = make_request(f"/api/problems/{problem_id}/attempts", token=token)
    print(f"Status: {status}, Attempts: {res}")
    assert status == 200, f"Expected 200, got {status}"
    assert len(res) >= 1
    
    # Test 12: Get Dashboard Summary
    print("\n[Test 12] GET /api/dashboard/summary")
    status, res = make_request("/api/dashboard/summary", token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    assert res.get("solved_count") == 1
    assert res.get("attempted_count") == 1
    
    # Test 13: AI Generate Explanation
    print(f"\n[Test 13] POST /api/ai/generate-explanation/{problem_id}")
    status, res = make_request(f"/api/ai/generate-explanation/{problem_id}", method="POST", token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 14: AI Generate Animation
    print(f"\n[Test 14] POST /api/ai/generate-animation/{problem_id}")
    status, res = make_request(f"/api/ai/generate-animation/{problem_id}", method="POST", token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 15: AI Review Code
    print("\n[Test 15] POST /api/ai/review-code")
    status, res = make_request("/api/ai/review-code", method="POST", data={
        "problem_id": problem_id,
        "submitted_code": "def solve(nums):\n    return False"
    }, token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 16: AI Hint
    print("\n[Test 16] POST /api/ai/hint")
    status, res = make_request("/api/ai/hint", method="POST", data={
        "problem_id": problem_id,
        "hint_level": 1
    }, token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 17: Generate Roadmap
    print("\n[Test 17] POST /api/roadmap/generate")
    status, res = make_request("/api/roadmap/generate", method="POST", token=token)
    print(f"Status: {status}, Response: {res}")
    assert status == 201, f"Expected 201, got {status}"
    
    # Test 18: Get Roadmaps
    print("\n[Test 18] GET /api/roadmap")
    status, res = make_request("/api/roadmap", token=token)
    print(f"Status: {status}, Roadmaps count: {len(res) if isinstance(res, list) else 'N/A'}")
    assert status == 200, f"Expected 200, got {status}"
    assert len(res) >= 1
    
    # Test 19: Get Revision items
    print("\n[Test 19] GET /api/revision")
    status, res = make_request("/api/revision", token=token)
    print(f"Status: {status}, Revision items: {res}")
    assert status == 200, f"Expected 200, got {status}"
    
    # Test 20: Import LeetCode URL
    print("\n[Test 20] POST /api/problems/import-leetcode-url")
    status, res = make_request("/api/problems/import-leetcode-url", method="POST", data={
        "url": "https://leetcode.com/problems/contains-duplicate/",
        "topic_id": 1,
        "pattern_id": 1,
        "difficulty": "Easy"
    }, token=token)
    print(f"Status: {status}, Response: {res}")
    assert status in (200, 201), f"Expected 200 or 201, got {status}"
    
    print("\n=== ALL API TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
