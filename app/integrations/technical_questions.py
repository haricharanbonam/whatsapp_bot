"""Technical Questions Integration: Daily MERN and SQL Query Challenges.

Provides curated question banks, AI-generated questions via Gemini,
and automated answer evaluation.
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Optional
import json

from openai import OpenAI
from app.core.config import settings

TZ = ZoneInfo(settings.SCHEDULER_TIMEZONE)

_ai_client = None

def get_ai_client():
    global _ai_client
    if _ai_client is None:
        api_key = settings.AI_API_KEY or "dummy_key_for_init"
        _ai_client = OpenAI(
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            api_key=api_key,
        )
    return _ai_client


# Curated High-Yield MERN Question Bank
MERN_QUESTIONS = [
    {
        "id": "mern-01",
        "topic": "React Hooks & Lifecycle",
        "question": (
            "In React 18+, what will be logged to the console when this component renders "
            "for the first time under StrictMode in development?\n\n"
            "```javascript\n"
            "function Counter() {\n"
            "  const [count, setCount] = useState(0);\n"
            "  useEffect(() => {\n"
            "    console.log('Mount: ' + count);\n"
            "    return () => console.log('Cleanup: ' + count);\n"
            "  }, []);\n"
            "  return <h1>{count}</h1>;\n"
            "}\n"
            "```"
        ),
        "options": [
            "A) Mount: 0",
            "B) Mount: 0 -> Cleanup: 0 -> Mount: 0",
            "C) Mount: 0 -> Mount: 0",
            "D) Mount: 0 -> Cleanup: 0"
        ],
        "answer": "B",
        "explanation": (
            "In React StrictMode (development only), React intentionally unmounts and "
            "remounts components once to verify that effects correctly clean up external "
            "subscriptions and timers."
        )
    },
    {
        "id": "mern-02",
        "topic": "Node.js Event Loop",
        "question": (
            "What is the exact execution order of logs in the Node.js event loop?\n\n"
            "```javascript\n"
            "console.log('1');\n"
            "setTimeout(() => console.log('2'), 0);\n"
            "Promise.resolve().then(() => console.log('3'));\n"
            "process.nextTick(() => console.log('4'));\n"
            "console.log('5');\n"
            "```"
        ),
        "options": [
            "A) 1, 5, 2, 3, 4",
            "B) 1, 5, 3, 4, 2",
            "C) 1, 5, 4, 3, 2",
            "D) 1, 4, 3, 5, 2"
        ],
        "answer": "C",
        "explanation": (
            "Synchronous code runs first (1, 5). Next, the microtask queue processes `process.nextTick` "
            "(4) before Promise microtasks (3). Finally, the macrotask/timer queue executes `setTimeout` (2)."
        )
    },
    {
        "id": "mern-03",
        "topic": "MongoDB Indexing",
        "question": (
            "Given the compound index `{ status: 1, createdAt: -1, userId: 1 }`, which of the "
            "following queries can NOT efficiently utilize this index (index prefix rule)?\n\n"
            "```javascript\n"
            "// Query 1: db.orders.find({ status: 'PAID' })\n"
            "// Query 2: db.orders.find({ status: 'PAID', createdAt: { $gt: ISODate(...) } })\n"
            "// Query 3: db.orders.find({ createdAt: { $gt: ISODate(...) }, userId: '123' })\n"
            "// Query 4: db.orders.find({ status: 'PAID', userId: '123' })\n"
            "```"
        ),
        "options": [
            "A) Query 1",
            "B) Query 2",
            "C) Query 3",
            "D) Query 4"
        ],
        "answer": "C",
        "explanation": (
            "MongoDB compound indexes follow the leftmost prefix rule. Query 3 lacks the leading "
            "`status` field, so the database engine cannot use the compound index prefix and must perform a collection scan."
        )
    },
    {
        "id": "mern-04",
        "topic": "Express.js Middleware Error Handling",
        "question": (
            "How does Express distinguish an error-handling middleware from a standard middleware?\n\n"
            "```javascript\n"
            "app.use((err, req, res, next) => {\n"
            "  console.error(err.stack);\n"
            "  res.status(500).send('Something broke!');\n"
            "});\n"
            "```"
        ),
        "options": [
            "A) By registering it with `app.useError()`",
            "B) By inspecting `middleware.length === 4` (function arity)",
            "C) By checking if `err instanceof Error`",
            "D) By placing it at the very top of `server.js`"
        ],
        "answer": "B",
        "explanation": (
            "Express inspects the function's `length` property (arity). A function with 4 parameters "
            "`(err, req, res, next)` is classified and routed as an error-handling middleware."
        )
    },
    {
        "id": "mern-05",
        "topic": "React State Management & Reconciliation",
        "question": (
            "Why is using array index as a `key` prop in React lists dangerous when list items can be reordered or removed?\n\n"
            "```jsx\n"
            "{items.map((item, index) => (\n"
            "  <TodoItem key={index} text={item.text} />\n"
            "))}\n"
            "```"
        ),
        "options": [
            "A) It causes syntax errors in JSX compilation",
            "B) React cannot track component identity, causing uncontrolled internal state (e.g. input values) to get attached to wrong items",
            "C) It disables React Fiber concurrent rendering completely",
            "D) It converts the component from functional to class-based"
        ],
        "answer": "B",
        "explanation": (
            "Keys allow React to preserve component identity across renders. When keys are indexes and an item is removed/prepended, "
            "React associates old component instances and their DOM state with the wrong data item."
        )
    }
]

# Curated High-Yield SQL Question Bank
SQL_QUESTIONS = [
    {
        "id": "sql-01",
        "topic": "Window Functions (Ranking)",
        "question": (
            "You have an `employees` table: `id`, `name`, `department_id`, `salary`.\n\n"
            "Write a SQL query to find the *2nd highest salary* in each department.\n"
            "If multiple employees share that salary, include all of them."
        ),
        "solution": (
            "```sql\n"
            "WITH RankedEmployees AS (\n"
            "  SELECT\n"
            "    department_id,\n"
            "    name,\n"
            "    salary,\n"
            "    DENSE_RANK() OVER (PARTITION BY department_id ORDER BY salary DESC) as rnk\n"
            "  FROM employees\n"
            ")\n"
            "SELECT department_id, name, salary\n"
            "FROM RankedEmployees\n"
            "WHERE rnk = 2;\n"
            "```"
        ),
        "hint": "Use `DENSE_RANK()` partitioned by department_id to handle salary ties without skipping ranks.",
        "key_concept": "DENSE_RANK() vs ROW_NUMBER() vs RANK()"
    },
    {
        "id": "sql-02",
        "topic": "Aggregations & HAVING Clause",
        "question": (
            "Given `customers (id, name)` and `orders (id, customer_id, order_date, amount)`:\n\n"
            "Write a query to find all customers who made more than 3 orders in 2026, "
            "and whose total order amount in 2026 exceeded $500."
        ),
        "solution": (
            "```sql\n"
            "SELECT\n"
            "  c.id,\n"
            "  c.name,\n"
            "  COUNT(o.id) AS total_orders,\n"
            "  SUM(o.amount) AS total_spent\n"
            "FROM customers c\n"
            "JOIN orders o ON c.id = o.customer_id\n"
            "WHERE o.order_date >= '2026-01-01' AND o.order_date < '2027-01-01'\n"
            "GROUP BY c.id, c.name\n"
            "HAVING COUNT(o.id) > 3 AND SUM(o.amount) > 500;\n"
            "```"
        ),
        "hint": "Filter date range in WHERE before grouping, and filter aggregate conditions in HAVING.",
        "key_concept": "WHERE (pre-aggregate filter) vs HAVING (post-aggregate filter)"
    },
    {
        "id": "sql-03",
        "topic": "Consecutive Active Days (Gaps and Islands)",
        "question": (
            "Given `user_logins (user_id, login_date)`:\n\n"
            "Write a query to find all users who logged in for at least 3 consecutive days."
        ),
        "solution": (
            "```sql\n"
            "WITH RankedLogins AS (\n"
            "  SELECT DISTINCT\n"
            "    user_id,\n"
            "    login_date,\n"
            "    DENSE_RANK() OVER (PARTITION BY user_id ORDER BY login_date) AS rnk\n"
            "  FROM user_logins\n"
            "),\n"
            "Groups AS (\n"
            "  SELECT\n"
            "    user_id,\n"
            "    login_date,\n"
            "    login_date - INTERVAL rnk DAY AS grp\n"
            "  FROM RankedLogins\n"
            ")\n"
            "SELECT user_id\n"
            "FROM Groups\n"
            "GROUP BY user_id, grp\n"
            "HAVING COUNT(*) >= 3;\n"
            "```"
        ),
        "hint": "Subtracting a sequential row rank from a date yields a constant date for consecutive intervals.",
        "key_concept": "Gaps and Islands problem using Date arithmetic & DENSE_RANK()"
    },
    {
        "id": "sql-04",
        "topic": "Self Joins / Hierarchy",
        "question": (
            "Given `employees (id, name, manager_id, salary)`:\n\n"
            "Find all employees who earn more than their direct manager."
        ),
        "solution": (
            "```sql\n"
            "SELECT\n"
            "  e.name AS employee_name,\n"
            "  e.salary AS employee_salary,\n"
            "  m.name AS manager_name,\n"
            "  m.salary AS manager_salary\n"
            "FROM employees e\n"
            "JOIN employees m ON e.manager_id = m.id\n"
            "WHERE e.salary > m.salary;\n"
            "```"
        ),
        "hint": "Join the table to itself using `e.manager_id = m.id`.",
        "key_concept": "Self Join on hierarchical relational data"
    }
]


def get_daily_mern_question(day_index: Optional[int] = None) -> dict:
    """Return today's MERN challenge deterministically based on day of year."""
    if day_index is None:
        day_index = datetime.now(TZ).timetuple().tm_yday
    idx = day_index % len(MERN_QUESTIONS)
    return MERN_QUESTIONS[idx]


def get_daily_sql_question(day_index: Optional[int] = None) -> dict:
    """Return today's SQL challenge deterministically based on day of year."""
    if day_index is None:
        day_index = datetime.now(TZ).timetuple().tm_yday
    idx = day_index % len(SQL_QUESTIONS)
    return SQL_QUESTIONS[idx]


def format_mern_question_message(q: dict) -> str:
    """Format MERN question cleanly for WhatsApp with monospace code block."""
    options_text = "\n".join(q.get("options", []))
    return (
        f"⚛️ *Daily MERN Question* · {q.get('topic')}\n\n"
        f"{q.get('question')}\n\n"
        f"*Options:*\n{options_text}\n\n"
        f"💡 _Reply with your option (A, B, C, or D) to check your answer!_"
    )


def format_sql_question_message(q: dict) -> str:
    """Format SQL query challenge cleanly for WhatsApp."""
    return (
        f"🗄️ *Daily SQL Query Challenge* · {q.get('topic')}\n\n"
        f"{q.get('question')}\n\n"
        f"💡 *Hint:* {q.get('hint')}\n\n"
        f"⚡ _Reply with your SQL query or thought process to get a review!_"
    )


async def generate_ai_technical_question(topic: str = "mern", difficulty: str = "medium") -> dict:
    """Generate fresh technical challenge dynamically using Gemini."""
    prompt = (
        f"Generate a unique {difficulty}-level interview challenge for {topic.upper()}.\n"
        "Return pure valid JSON with these keys:\n"
        "- 'topic': concise concept title\n"
        "- 'question': clear question with code snippet in markdown block (```javascript or ```sql)\n"
        "- 'options': list of 4 multiple-choice options (if conceptual) or [] (if query/coding)\n"
        "- 'answer': correct option letter or query summary\n"
        "- 'explanation': deep 2-3 sentence technical explanation"
    )

    try:
        ai = get_ai_client()
        response = ai.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "You are a senior full-stack engineer and tech interviewer. Output JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        print(f"[technical_questions error] AI generation failed: {e}")
        return get_daily_mern_question() if topic.lower() == "mern" else get_daily_sql_question()


async def evaluate_user_technical_answer(category: str, question_text: str, user_answer: str) -> str:
    """Evaluate user's technical answer with constructive critique."""
    prompt = (
        f"You are Bro-bot, Haricharan's tech mentor on WhatsApp.\n"
        f"Category: {category}\n"
        f"Question: {question_text}\n"
        f"User's Answer: {user_answer}\n\n"
        "Provide a concise, encouraging WhatsApp-formatted critique (2-4 lines max):\n"
        "1. Direct verdict (Correct ✅ / Partial ⚠️ / Incorrect ❌)\n"
        "2. The 'why' behind it or what edge cases were missed\n"
        "3. Keep the tone friendly, sharp and bro-like with sparse emojis."
    )

    try:
        ai = get_ai_client()
        response = ai.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "You are Bro-bot, a top-tier fullstack mentor on WhatsApp. Keep response under 5 lines."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"[Bot]: Could not evaluate answer right now: {e}"
