# init_db.py
import sys
import os

# Append current directory to path so app module can be found
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import SQLModel, Session, select
from app.database import engine
from app.config import settings
from app.models import DSATopic, DSAPattern, DSAProblem, Role

# Import models so SQLModel metadata is aware of them
from app import models

def seed_database():
    print("Seeding database with default roles, DSA topics, patterns, and problems...")
    with Session(engine) as session:
        # 0. Seed Roles
        for role_name in ("user", "admin"):
            if not session.exec(select(Role).where(Role.name == role_name)).first():
                session.add(Role(name=role_name))
        session.commit()
        # 1. Seed Topics
        topics_data = [
            ("Arrays & Hashing", "Problems relating to array manipulation, key-value mapping, and prefix logic."),
            ("Two Pointers", "Linear traversal patterns using multiple pointers tracking positions."),
            ("Sliding Window", "Subarray optimization patterns tracking dynamic or fixed boundaries."),
            ("Stack", "Last-in-first-out data structures tracking bracket validation or mono-stacks."),
            ("Binary Search", "Logarithmic search algorithms on sorted linear sequences.")
        ]
        
        topics = []
        for name, desc in topics_data:
            stmt = select(DSATopic).where(DSATopic.name == name)
            existing = session.exec(stmt).first()
            if not existing:
                topic = DSATopic(name=name, description=desc)
                session.add(topic)
                topics.append(topic)
            else:
                topics.append(existing)
        
        session.commit()
        for t in topics:
            session.refresh(t)
            
        # 2. Seed Patterns
        patterns_data = [
            (topics[0].id, "Hashing", "Using a hash table or set to track occurrences of elements in O(N)."),
            (topics[0].id, "Prefix Sum", "Precomputing cumulative sums to answer subarray queries in O(1)."),
            (topics[1].id, "Two Pointers", "Iterating from both ends of the list or offset indices in O(N)."),
            (topics[2].id, "Sliding Window", "Tracking contiguous subsets of elements with dynamic window shifts."),
            (topics[3].id, "Stack", "Validating balanced strings or elements tracking with helper collections."),
            (topics[4].id, "Binary Search", "Dividing sorted search intervals by half in O(log N).")
        ]
        
        patterns = []
        for topic_id, name, desc in patterns_data:
            stmt = select(DSAPattern).where(DSAPattern.name == name, DSAPattern.topic_id == topic_id)
            existing = session.exec(stmt).first()
            if not existing:
                pattern = DSAPattern(topic_id=topic_id, name=name, description=desc)
                session.add(pattern)
                patterns.append(pattern)
            else:
                patterns.append(existing)
                
        session.commit()
        for p in patterns:
            session.refresh(p)
            
        # 3. Seed Sample Problems
        problems_data = [
            {
                "title": "Two Sum",
                "difficulty": "Easy",
                "topic_id": topics[0].id,
                "pattern_id": patterns[0].id,
                "leetcode_slug": "two-sum",
                "leetcode_url": "https://leetcode.com/problems/two-sum/",
                "description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.\n\nYou may assume that each input would have exactly one solution, and you may not use the same element twice.",
                "constraints_text": "2 <= nums.length <= 10^4\n-10^9 <= nums[i] <= 10^9\n-10^9 <= target <= 10^9\nOnly one valid answer exists.",
                "starter_code": "def twoSum(nums, target):\n    # Write Python here\n    pass",
                "examples": [
                    {"input": "nums = [2,7,11,15], target = 9", "output": "[0,1]", "explanation": "Because nums[0] + nums[1] == 9, we return [0, 1]."}
                ]
            },
            {
                "title": "Valid Palindrome",
                "difficulty": "Easy",
                "topic_id": topics[1].id,
                "pattern_id": patterns[2].id,
                "leetcode_slug": "valid-palindrome",
                "leetcode_url": "https://leetcode.com/problems/valid-palindrome/",
                "description": "A phrase is a palindrome if, after converting all uppercase letters into lowercase letters and removing all non-alphanumeric characters, it reads the same forward and backward. Alphanumeric characters include letters and numbers.",
                "constraints_text": "1 <= s.length <= 2 * 10^5\ns consists only of printable ASCII characters.",
                "starter_code": "def isPalindrome(s):\n    # Write Python here\n    pass",
                "examples": [
                    {"input": "s = \"A man, a plan, a canal: Panama\"", "output": "true", "explanation": "\"amanaplanacanalpanama\" is a palindrome."}
                ]
            },
            {
                "title": "Binary Search",
                "difficulty": "Easy",
                "topic_id": topics[4].id,
                "pattern_id": patterns[5].id,
                "leetcode_slug": "binary-search",
                "leetcode_url": "https://leetcode.com/problems/binary-search/",
                "description": "Given an array of integers nums which is sorted in ascending order, and an integer target, write a function to search target in nums. If target exists, then return its index. Otherwise, return -1.",
                "constraints_text": "1 <= nums.length <= 10^4\n-10^4 < nums[i], target < 10^4\nAll the integers in nums are unique.\nnums is sorted in ascending order.",
                "starter_code": "def search(nums, target):\n    # Write Python here\n    pass",
                "examples": [
                    {"input": "nums = [-1,0,3,5,9,12], target = 9", "output": "4", "explanation": "9 exists in nums and its index is 4"}
                ]
            }
        ]
        
        for prob in problems_data:
            stmt = select(DSAProblem).where(DSAProblem.leetcode_slug == prob["leetcode_slug"])
            existing = session.exec(stmt).first()
            if not existing:
                problem = DSAProblem(
                    title=prob["title"],
                    difficulty=prob["difficulty"],
                    topic_id=prob["topic_id"],
                    pattern_id=prob["pattern_id"],
                    leetcode_slug=prob["leetcode_slug"],
                    leetcode_url=prob["leetcode_url"],
                    description=prob["description"],
                    constraints_text=prob["constraints_text"],
                    starter_code=prob["starter_code"],
                    examples=prob["examples"]
                )
                session.add(problem)
                
        session.commit()
    print("Database seeding completed successfully!")

def create_db_and_tables():
    print(f"Connecting to database at: {settings.DATABASE_URL.split('@')[-1]}...")
    try:
        # Bootstrap a fresh database: create the full current schema, then mark
        # it as up to date for Alembic so future `alembic upgrade head` runs
        # only apply migrations created after this point.
        SQLModel.metadata.create_all(engine)
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)), "alembic.ini"))
        command.stamp(alembic_cfg, "head")
        print("Success: Database tables created and stamped at Alembic head!")
        seed_database()
    except Exception as e:
        print("\n[ERROR] Failed to initialize database tables.", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        print("\nPlease make sure that:", file=sys.stderr)
        print("1. Your PostgreSQL server is running.", file=sys.stderr)
        print("2. You have created the target database (e.g. 'algolens_db').", file=sys.stderr)
        print("3. Your credentials in backend/.env are correct.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    create_db_and_tables()
