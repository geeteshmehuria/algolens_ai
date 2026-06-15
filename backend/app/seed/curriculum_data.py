"""The full AlgoLens AI DSA curriculum.

Single source of truth for the topic/subtopic catalogue. Consumed by
``app.seed.curriculum.seed_curriculum`` which upserts every entry into
``dsa_topics`` keyed on a slug derived from the (globally unique) name.

Data shape per category::

    {
        "category": "Arrays",
        "prerequisites": ["array-traversal"],   # category-level prereq slugs
        "topics": [
            ("Two Pointers", "beginner", "Solve array/string problems with two moving pointers."),
            ...
        ],
    }

Each topic tuple is ``(name, difficulty, description)``. ``estimated_time_minutes``
is derived from difficulty in the seeder. Names are globally unique so the
derived slug is unique too (concepts that recur across categories are
disambiguated, e.g. "Two Pointers" vs "Two Pointers on Strings" vs
"Two Pointers Pattern").
"""

# Minutes assigned per difficulty when none is given explicitly.
DIFFICULTY_MINUTES = {"beginner": 25, "intermediate": 40, "advanced": 60}

# Legacy topic names (created by the original init_db seed) mapped to the
# canonical curriculum name they should be merged into. Lets the seeder reuse
# the existing row (and keep its problem links) instead of creating a duplicate.
LEGACY_ALIASES = {
    "Stack Basics": "Stack",
}

CURRICULUM = [
    {
        "category": "Programming Basics",
        "prerequisites": [],
        "topics": [
            (
                "Input and Output",
                "beginner",
                "Read input and print formatted output in your language of choice.",
            ),
            (
                "Variables and Data Types",
                "beginner",
                "Integers, floats, booleans, strings and how memory holds them.",
            ),
            (
                "Operators",
                "beginner",
                "Arithmetic, comparison, logical and assignment operators and precedence.",
            ),
            (
                "Conditionals",
                "beginner",
                "Branching with if / elif / else and boolean expressions.",
            ),
            (
                "Loops",
                "beginner",
                "Iterate with for and while loops, break and continue.",
            ),
            (
                "Functions",
                "beginner",
                "Define, call and return from functions; parameters and scope.",
            ),
            (
                "Recursion Basics",
                "beginner",
                "Functions that call themselves: base case, recursive case, the call stack.",
            ),
            (
                "Time and Space Complexity Basics",
                "beginner",
                "Reason about how runtime and memory grow with input size.",
            ),
        ],
    },
    {
        "category": "Complexity Analysis",
        "prerequisites": ["recursion-basics", "time-and-space-complexity-basics"],
        "topics": [
            (
                "Big-O Notation",
                "beginner",
                "Upper-bound asymptotic notation for worst-case growth.",
            ),
            (
                "Big Omega and Big Theta",
                "intermediate",
                "Lower-bound and tight-bound asymptotic notation.",
            ),
            (
                "Best Average and Worst Case",
                "intermediate",
                "How input shape changes an algorithm's running time.",
            ),
            (
                "Time Complexity Patterns",
                "intermediate",
                "Recognise O(1), O(log n), O(n), O(n log n), O(n^2) from code shape.",
            ),
            (
                "Space Complexity",
                "intermediate",
                "Auxiliary vs total memory, recursion stack, in-place algorithms.",
            ),
            (
                "Amortized Analysis",
                "advanced",
                "Average cost per operation over a sequence (e.g. dynamic arrays).",
            ),
        ],
    },
    {
        "category": "Arrays",
        "prerequisites": ["loops", "time-and-space-complexity-basics"],
        "topics": [
            (
                "Arrays & Hashing",
                "intermediate",
                "Array manipulation combined with hash maps/sets for O(n) lookups.",
            ),
            (
                "Array Traversal",
                "beginner",
                "Iterate, index and mutate one-dimensional arrays safely.",
            ),
            (
                "Prefix Sums",
                "intermediate",
                "Precompute cumulative sums to answer range queries in O(1).",
            ),
            (
                "Difference Arrays",
                "intermediate",
                "Apply range updates in O(1) and reconstruct the final array.",
            ),
            (
                "Kadane's Algorithm",
                "intermediate",
                "Maximum subarray sum in a single linear pass.",
            ),
            (
                "Two Pointers",
                "beginner",
                "Solve array problems with two moving pointers from ends or offsets.",
            ),
            (
                "Sliding Window",
                "intermediate",
                "Optimise contiguous-subarray problems with a moving window.",
            ),
            (
                "Sorting-Based Array Problems",
                "intermediate",
                "Unlock problems by sorting first, then scanning.",
            ),
            (
                "Matrix Basics",
                "beginner",
                "Represent and traverse 2D grids by row and column.",
            ),
            (
                "2D Arrays",
                "intermediate",
                "Rotate, transpose and search two-dimensional arrays.",
            ),
        ],
    },
    {
        "category": "Strings",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "String Traversal",
                "beginner",
                "Iterate characters, handle immutability and build strings efficiently.",
            ),
            (
                "Character Frequency",
                "beginner",
                "Count characters with arrays or hash maps.",
            ),
            (
                "Two Pointers on Strings",
                "beginner",
                "Compare or shrink strings from both ends.",
            ),
            (
                "Sliding Window on Strings",
                "intermediate",
                "Longest/shortest substring problems with a moving window.",
            ),
            (
                "Pattern Matching Basics",
                "intermediate",
                "Find substrings; intro to KMP and naive matching.",
            ),
            (
                "Palindrome Problems",
                "beginner",
                "Detect and build palindromes with pointers and expansion.",
            ),
            (
                "Anagrams",
                "beginner",
                "Group and detect anagrams via sorting or frequency counts.",
            ),
            (
                "String Hashing Basics",
                "advanced",
                "Rolling hashes for fast substring comparison.",
            ),
        ],
    },
    {
        "category": "Recursion and Backtracking",
        "prerequisites": ["recursion-basics"],
        "topics": [
            (
                "Recursion Tree",
                "intermediate",
                "Visualise recursive calls to reason about work and depth.",
            ),
            (
                "Base Case and Recursive Case",
                "beginner",
                "Design correct termination and reduction steps.",
            ),
            (
                "Subsets",
                "intermediate",
                "Generate the power set with include/exclude recursion.",
            ),
            (
                "Permutations",
                "intermediate",
                "Enumerate all orderings with swapping or visited tracking.",
            ),
            (
                "Combinations",
                "intermediate",
                "Choose k of n with ordered recursive selection.",
            ),
            (
                "N-Queens",
                "advanced",
                "Place queens with backtracking and conflict checks.",
            ),
            (
                "Sudoku Solver",
                "advanced",
                "Fill a grid with constraint-checked backtracking.",
            ),
            (
                "Backtracking Pruning",
                "advanced",
                "Cut search branches early to make backtracking feasible.",
            ),
        ],
    },
    {
        "category": "Searching",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "Linear Search",
                "beginner",
                "Scan every element until the target is found.",
            ),
            (
                "Binary Search",
                "beginner",
                "Halve a sorted search space each step for O(log n) lookup.",
            ),
            (
                "Binary Search on Answer",
                "advanced",
                "Binary search over a monotonic answer space, not the array.",
            ),
            (
                "Lower Bound and Upper Bound",
                "intermediate",
                "Find first/last positions satisfying a predicate.",
            ),
            (
                "Search in Rotated Sorted Array",
                "intermediate",
                "Binary search across a rotation pivot.",
            ),
            (
                "Peak Element",
                "intermediate",
                "Find a local maximum in O(log n) with binary search.",
            ),
            (
                "Matrix Search",
                "intermediate",
                "Search row/column-sorted matrices efficiently.",
            ),
        ],
    },
    {
        "category": "Sorting",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "Bubble Sort",
                "beginner",
                "Repeatedly swap adjacent out-of-order elements.",
            ),
            (
                "Selection Sort",
                "beginner",
                "Select the minimum each pass and place it.",
            ),
            (
                "Insertion Sort",
                "beginner",
                "Build a sorted prefix by inserting each element.",
            ),
            (
                "Merge Sort",
                "intermediate",
                "Divide, sort halves, and merge in O(n log n).",
            ),
            ("Quick Sort", "intermediate", "Partition around a pivot and recurse."),
            (
                "Counting Sort",
                "intermediate",
                "Sort small-range integers in linear time.",
            ),
            (
                "Radix Sort",
                "advanced",
                "Sort by digit/position using a stable subsort.",
            ),
            (
                "Custom Sorting",
                "beginner",
                "Sort by keys/comparators for problem-specific orders.",
            ),
            (
                "Sorting Stability",
                "intermediate",
                "When equal keys keep their relative order, and why it matters.",
            ),
        ],
    },
    {
        "category": "Linked List",
        "prerequisites": ["recursion-basics"],
        "topics": [
            (
                "Singly Linked List",
                "beginner",
                "Nodes with a single next pointer; insert, delete, traverse.",
            ),
            (
                "Doubly Linked List",
                "intermediate",
                "Bidirectional nodes with prev and next pointers.",
            ),
            (
                "Fast and Slow Pointers",
                "intermediate",
                "Tortoise-and-hare traversal for middle/cycle problems.",
            ),
            (
                "Reverse Linked List",
                "beginner",
                "Reverse pointers iteratively and recursively.",
            ),
            (
                "Cycle Detection (Floyd)",
                "intermediate",
                "Detect and locate a loop using two-speed pointers.",
            ),
            (
                "Merge Linked Lists",
                "intermediate",
                "Merge sorted lists into one ordered list.",
            ),
            (
                "Remove Nth Node",
                "intermediate",
                "Delete from the end in one pass with a gap pointer.",
            ),
            (
                "Linked List Intersection",
                "intermediate",
                "Find the node where two lists converge.",
            ),
        ],
    },
    {
        "category": "Stack",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "Stack Basics",
                "beginner",
                "Last-in-first-out structure: push, pop, peek.",
            ),
            (
                "Monotonic Stack",
                "intermediate",
                "Maintain an increasing/decreasing stack for range queries.",
            ),
            (
                "Next Greater Element",
                "intermediate",
                "Find the next larger value for each element with a stack.",
            ),
            (
                "Previous Smaller Element",
                "intermediate",
                "Find the nearest smaller value to the left.",
            ),
            (
                "Valid Parentheses",
                "beginner",
                "Validate balanced brackets with a stack.",
            ),
            (
                "Min Stack",
                "intermediate",
                "Support push/pop/min in O(1) using an auxiliary stack.",
            ),
            (
                "Expression Evaluation",
                "intermediate",
                "Evaluate infix/postfix expressions with stacks.",
            ),
        ],
    },
    {
        "category": "Queue and Deque",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "Queue Basics",
                "beginner",
                "First-in-first-out structure: enqueue and dequeue.",
            ),
            (
                "Circular Queue",
                "intermediate",
                "Fixed-size queue that wraps around its buffer.",
            ),
            (
                "Deque",
                "intermediate",
                "Double-ended queue with O(1) push/pop at both ends.",
            ),
            (
                "Monotonic Queue",
                "advanced",
                "Maintain ordered extremes for window problems.",
            ),
            (
                "Sliding Window Maximum",
                "advanced",
                "Track the max of each window with a deque.",
            ),
            (
                "BFS Queue Usage",
                "intermediate",
                "Use a queue to explore level by level.",
            ),
        ],
    },
    {
        "category": "Hashing",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "HashMap Basics",
                "beginner",
                "Key-value storage with average O(1) operations.",
            ),
            (
                "HashSet Basics",
                "beginner",
                "Membership testing and de-duplication in O(1).",
            ),
            (
                "Frequency Maps",
                "beginner",
                "Count occurrences to drive counting/grouping logic.",
            ),
            (
                "Prefix Sum with HashMap",
                "intermediate",
                "Count subarrays with a target sum using running sums.",
            ),
            ("Duplicate Detection", "beginner", "Spot repeats with a set or map."),
            (
                "Grouping Problems",
                "intermediate",
                "Bucket items by a computed key (e.g. anagram groups).",
            ),
            (
                "Hash Collision Concept",
                "intermediate",
                "How hashing handles collisions: chaining and open addressing.",
            ),
        ],
    },
    {
        "category": "Trees",
        "prerequisites": ["recursion-basics"],
        "topics": [
            (
                "Binary Tree Basics",
                "beginner",
                "Nodes, children, leaves; build and represent binary trees.",
            ),
            (
                "Tree Traversal",
                "intermediate",
                "Inorder, preorder and postorder depth-first walks.",
            ),
            (
                "Level Order Traversal",
                "intermediate",
                "Breadth-first traversal across tree levels.",
            ),
            (
                "Tree Height and Depth",
                "beginner",
                "Compute depth, height and balance of a tree.",
            ),
            ("Tree Diameter", "intermediate", "Longest path between any two nodes."),
            ("Path Sum", "intermediate", "Find root-to-leaf or any-path sums."),
            (
                "Lowest Common Ancestor",
                "intermediate",
                "Find the deepest shared ancestor of two nodes.",
            ),
            (
                "Tree Construction",
                "advanced",
                "Rebuild trees from traversal orderings.",
            ),
            (
                "Tree Serialization",
                "advanced",
                "Encode and decode a tree to and from a string.",
            ),
        ],
    },
    {
        "category": "Binary Search Tree",
        "prerequisites": ["binary-tree-basics"],
        "topics": [
            ("BST Properties", "beginner", "Ordering invariant: left < node < right."),
            (
                "BST Search Insert Delete",
                "intermediate",
                "Maintain the BST invariant through mutations.",
            ),
            (
                "Validate BST",
                "intermediate",
                "Verify the ordering property with bounds or inorder.",
            ),
            (
                "Kth Smallest in BST",
                "intermediate",
                "Use inorder traversal to find ranked elements.",
            ),
            (
                "Floor and Ceil in BST",
                "intermediate",
                "Find closest smaller/larger values.",
            ),
            (
                "LCA in BST",
                "intermediate",
                "Exploit ordering to find ancestors in O(h).",
            ),
        ],
    },
    {
        "category": "Heap / Priority Queue",
        "prerequisites": ["array-traversal"],
        "topics": [
            (
                "Min Heap",
                "intermediate",
                "Complete binary tree with the smallest element on top.",
            ),
            (
                "Max Heap",
                "intermediate",
                "Heap variant with the largest element on top.",
            ),
            (
                "K Largest Elements",
                "intermediate",
                "Maintain a size-k heap to find top elements.",
            ),
            (
                "Top K Frequent Elements",
                "intermediate",
                "Combine frequency counts with a heap.",
            ),
            (
                "Merge K Sorted Lists",
                "advanced",
                "Merge many sorted sequences with a heap.",
            ),
            (
                "Median from Data Stream",
                "advanced",
                "Track a running median with two heaps.",
            ),
        ],
    },
    {
        "category": "Graphs",
        "prerequisites": ["queue-basics", "recursion-basics"],
        "topics": [
            (
                "Graph Representation",
                "beginner",
                "Adjacency list vs matrix; directed vs undirected.",
            ),
            (
                "BFS (Breadth-First Search)",
                "intermediate",
                "Explore graphs level by level with a queue.",
            ),
            (
                "DFS (Depth-First Search)",
                "intermediate",
                "Explore graphs deeply with recursion or a stack.",
            ),
            (
                "Connected Components",
                "intermediate",
                "Count and label disconnected regions.",
            ),
            (
                "Cycle Detection (Graph)",
                "intermediate",
                "Detect cycles in directed and undirected graphs.",
            ),
            (
                "Bipartite Graph",
                "intermediate",
                "Two-colour a graph to test bipartiteness.",
            ),
            ("Topological Sort", "intermediate", "Order a DAG so edges point forward."),
            (
                "Shortest Path Basics",
                "intermediate",
                "Unweighted shortest paths with BFS.",
            ),
            (
                "Dijkstra",
                "advanced",
                "Single-source shortest paths with non-negative weights.",
            ),
            (
                "Bellman-Ford",
                "advanced",
                "Shortest paths that tolerate negative edges.",
            ),
            (
                "Floyd-Warshall",
                "advanced",
                "All-pairs shortest paths via dynamic programming.",
            ),
            (
                "Minimum Spanning Tree",
                "advanced",
                "Connect all nodes with minimum total edge weight.",
            ),
            ("Prim's Algorithm", "advanced", "Grow an MST from a node using a heap."),
            (
                "Kruskal's Algorithm",
                "advanced",
                "Build an MST by adding cheapest safe edges.",
            ),
            (
                "Disjoint Set Union",
                "advanced",
                "Union-find with path compression and rank.",
            ),
        ],
    },
    {
        "category": "Dynamic Programming",
        "prerequisites": ["recursion-basics"],
        "topics": [
            (
                "DP Basics",
                "intermediate",
                "Optimal substructure and overlapping subproblems.",
            ),
            ("Memoization", "intermediate", "Top-down DP caching recursive results."),
            ("Tabulation", "intermediate", "Bottom-up DP filling a table iteratively."),
            (
                "1D DP",
                "intermediate",
                "State over a single dimension (e.g. climbing stairs).",
            ),
            (
                "2D DP",
                "intermediate",
                "State over two dimensions (grids, two sequences).",
            ),
            (
                "0/1 Knapsack",
                "advanced",
                "Choose items under a weight budget, each at most once.",
            ),
            (
                "Unbounded Knapsack",
                "advanced",
                "Knapsack where items can be reused (coin change).",
            ),
            (
                "Longest Common Subsequence",
                "advanced",
                "Align two sequences for the longest shared order.",
            ),
            (
                "Longest Increasing Subsequence",
                "advanced",
                "Find the longest rising subsequence in O(n log n).",
            ),
            (
                "Matrix Chain Multiplication",
                "advanced",
                "Optimal parenthesisation interval DP.",
            ),
            (
                "DP on Strings",
                "advanced",
                "Edit distance and substring/subsequence DP.",
            ),
            ("DP on Trees", "advanced", "Aggregate subtree results with rerooting."),
            (
                "DP on Grids",
                "intermediate",
                "Path counting and min-cost paths on a grid.",
            ),
            ("Bitmask DP Basics", "advanced", "Encode subsets as bitmasks for state."),
        ],
    },
    {
        "category": "Greedy Algorithms",
        "prerequisites": ["custom-sorting"],
        "topics": [
            (
                "Greedy Intuition",
                "intermediate",
                "When locally optimal choices yield a global optimum.",
            ),
            (
                "Activity Selection",
                "intermediate",
                "Maximise non-overlapping activities by end time.",
            ),
            (
                "Interval Scheduling",
                "intermediate",
                "Pick a maximum compatible set of intervals.",
            ),
            (
                "Interval Merging (Greedy)",
                "intermediate",
                "Combine overlapping intervals after sorting.",
            ),
            (
                "Jump Game",
                "intermediate",
                "Reach the end greedily by tracking the farthest index.",
            ),
            (
                "Fractional Knapsack",
                "intermediate",
                "Take item fractions by value-per-weight ratio.",
            ),
            (
                "Huffman Coding Concept",
                "advanced",
                "Build optimal prefix codes with a greedy heap.",
            ),
            (
                "Gas Station",
                "intermediate",
                "Find a valid circular start with a running balance.",
            ),
            (
                "Minimum Platforms",
                "intermediate",
                "Count peak overlaps using sorted arrivals/departures.",
            ),
        ],
    },
    {
        "category": "Intervals",
        "prerequisites": ["custom-sorting"],
        "topics": [
            (
                "Merge Intervals",
                "intermediate",
                "Sort and coalesce overlapping intervals.",
            ),
            (
                "Insert Interval",
                "intermediate",
                "Insert and merge a new interval into a sorted set.",
            ),
            (
                "Meeting Rooms",
                "intermediate",
                "Decide attendance / count rooms from intervals.",
            ),
            (
                "Overlapping Intervals",
                "intermediate",
                "Detect and count interval overlaps.",
            ),
            (
                "Sweep Line Basics",
                "advanced",
                "Process sorted events to answer range questions.",
            ),
        ],
    },
    {
        "category": "Tries",
        "prerequisites": ["string-traversal"],
        "topics": [
            (
                "Trie Basics",
                "intermediate",
                "Prefix tree storing strings character by character.",
            ),
            (
                "Trie Insert Search Prefix",
                "intermediate",
                "Insert words and query exact/prefix matches.",
            ),
            ("Word Dictionary", "advanced", "Support wildcard search over a trie."),
            (
                "Word Search",
                "advanced",
                "Find dictionary words on a grid using a trie + DFS.",
            ),
            (
                "Auto-Complete",
                "advanced",
                "Suggest completions by walking trie subtrees.",
            ),
            (
                "Maximum XOR Using Trie",
                "advanced",
                "Maximise XOR pairs with a binary trie.",
            ),
        ],
    },
    {
        "category": "Bit Manipulation",
        "prerequisites": ["operators"],
        "topics": [
            ("Bitwise Operators", "beginner", "AND, OR, XOR, NOT and shifts."),
            (
                "Check Set Clear Toggle Bit",
                "beginner",
                "Manipulate individual bits with masks.",
            ),
            (
                "Count Set Bits",
                "beginner",
                "Population count via Brian Kernighan's trick.",
            ),
            (
                "Power of Two",
                "beginner",
                "Detect powers of two with a single bit test.",
            ),
            (
                "XOR Problems",
                "intermediate",
                "Find unique/missing numbers with XOR properties.",
            ),
            (
                "Subsets Using Bits",
                "intermediate",
                "Enumerate subsets by iterating bitmasks.",
            ),
            (
                "Bitmasking Basics",
                "intermediate",
                "Represent and combine state compactly with bits.",
            ),
        ],
    },
    {
        "category": "Math for DSA",
        "prerequisites": ["loops"],
        "topics": [
            (
                "GCD and LCM",
                "beginner",
                "Euclidean algorithm and least common multiple.",
            ),
            ("Prime Numbers", "beginner", "Primality testing up to the square root."),
            ("Sieve of Eratosthenes", "intermediate", "Precompute all primes up to n."),
            (
                "Modular Arithmetic",
                "intermediate",
                "Work under a modulus; inverses and properties.",
            ),
            (
                "Fast Exponentiation",
                "intermediate",
                "Compute powers in O(log n) by squaring.",
            ),
            (
                "Combinatorics Basics",
                "intermediate",
                "Counting with permutations and combinations.",
            ),
            (
                "Number Theory Basics",
                "advanced",
                "Divisors, factorisation and modular identities.",
            ),
        ],
    },
    {
        "category": "Advanced Data Structures",
        "prerequisites": ["binary-tree-basics"],
        "topics": [
            (
                "Segment Tree",
                "advanced",
                "Range queries and point updates in O(log n).",
            ),
            (
                "Fenwick Tree (BIT)",
                "advanced",
                "Prefix-sum queries/updates with a binary indexed tree.",
            ),
            (
                "Sparse Table",
                "advanced",
                "O(1) idempotent range queries after O(n log n) prep.",
            ),
            (
                "Ordered Set Concept",
                "advanced",
                "Balanced-BST set supporting rank/range queries.",
            ),
            ("LRU Cache", "intermediate", "Evict least-recently-used items in O(1)."),
            ("LFU Cache", "advanced", "Evict least-frequently-used items in O(1)."),
        ],
    },
    {
        "category": "Advanced Graphs",
        "prerequisites": ["dfs-depth-first-search", "bfs-breadth-first-search"],
        "topics": [
            (
                "Strongly Connected Components",
                "advanced",
                "Maximal mutually-reachable subgraphs in a digraph.",
            ),
            ("Kosaraju Algorithm", "advanced", "Find SCCs with two DFS passes."),
            (
                "Tarjan Algorithm",
                "advanced",
                "Find SCCs in one DFS using low-link values.",
            ),
            (
                "Bridges and Articulation Points",
                "advanced",
                "Find critical edges and vertices.",
            ),
            (
                "Network Flow Basics",
                "advanced",
                "Max-flow / min-cut with augmenting paths.",
            ),
        ],
    },
    {
        "category": "Design / System-style Coding",
        "prerequisites": ["hashmap-basics"],
        "topics": [
            (
                "Design LRU Cache",
                "intermediate",
                "Hash map + doubly linked list for O(1) cache ops.",
            ),
            (
                "Design LFU Cache",
                "advanced",
                "Frequency buckets for O(1) least-frequent eviction.",
            ),
            (
                "Design Twitter",
                "advanced",
                "Feed merge with heaps and follow relationships.",
            ),
            (
                "Design Browser History",
                "intermediate",
                "Back/forward navigation with two stacks or a list.",
            ),
            (
                "Design HashMap",
                "intermediate",
                "Implement a hash map from scratch with buckets.",
            ),
            (
                "Design Stack and Queue Variants",
                "intermediate",
                "Build min-stack, queue-from-stacks and similar.",
            ),
        ],
    },
    {
        "category": "Interview Patterns",
        "prerequisites": ["two-pointers", "sliding-window"],
        "topics": [
            (
                "Two Pointers Pattern",
                "intermediate",
                "Recognise and apply the two-pointers template.",
            ),
            (
                "Sliding Window Pattern",
                "intermediate",
                "Template for fixed/variable window subarray problems.",
            ),
            (
                "Fast and Slow Pointers Pattern",
                "intermediate",
                "Cycle and midpoint template across structures.",
            ),
            (
                "Merge Intervals Pattern",
                "intermediate",
                "General overlap-merging template.",
            ),
            (
                "Cyclic Sort Pattern",
                "intermediate",
                "Place numbers 1..n at their index in O(n).",
            ),
            (
                "Top K Elements Pattern",
                "intermediate",
                "Heap template for top/closest/frequent k.",
            ),
            (
                "K-way Merge Pattern",
                "advanced",
                "Merge multiple sorted inputs with a heap.",
            ),
            (
                "Backtracking Pattern",
                "advanced",
                "General choose/explore/un-choose template.",
            ),
            (
                "BFS Pattern",
                "intermediate",
                "Template for shortest-path and level problems.",
            ),
            (
                "DFS Pattern",
                "intermediate",
                "Template for exhaustive/connectivity traversal.",
            ),
            (
                "Dynamic Programming Patterns",
                "advanced",
                "Identify state, transition and base case quickly.",
            ),
            (
                "Greedy Patterns",
                "intermediate",
                "Spot exchange-argument and sorting-based greedies.",
            ),
        ],
    },
]
