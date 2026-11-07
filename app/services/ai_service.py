import json
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.core.config import settings
from app.services.leetcode_service import fetch_daily_question, fetch_activity
from app.integrations.calendar import fetch_daily_events, format_events_message
from app.integrations.reminders import create_reminder
from app.integrations.technical_questions import (
    get_daily_mern_question,
    get_daily_sql_question,
    format_mern_question_message,
    format_sql_question_message,
    generate_ai_technical_question,
    evaluate_user_technical_answer,
)
from app.integrations.focus_session import (
    record_paid_burst_checkin,
    get_paid_burst_stats,
)

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


TZ = ZoneInfo(settings.SCHEDULER_TIMEZONE)
MAX_TOOL_ITERATIONS = 4

AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_daily_mern_question",
            "description": (
                "Fetch today's daily MERN (MongoDB, Express, React, Node.js) technical question. "
                "Use whenever the user asks for a MERN question, React/Node quiz, or says 'mern'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "generate_fresh": {
                        "type": "boolean",
                        "description": "If true, generates a brand new dynamic question using AI.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_sql_question",
            "description": (
                "Fetch today's daily SQL Query Challenge (window functions, joins, aggregations, optimization). "
                "Use whenever the user asks for a SQL challenge, database query, or says 'sql'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "generate_fresh": {
                        "type": "boolean",
                        "description": "If true, generates a brand new dynamic SQL question using AI.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "evaluate_technical_answer",
            "description": (
                "Evaluate the user's technical answer or SQL query, providing constructive feedback and verification."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["mern", "sql"],
                        "description": "The category of the question being answered.",
                    },
                    "question_context": {
                        "type": "string",
                        "description": "Summary of the question being answered.",
                    },
                    "user_answer": {
                        "type": "string",
                        "description": "The user's code, query, or option answer.",
                    },
                },
                "required": ["category", "user_answer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkin_paid_burst",
            "description": (
                "Record the user's check-in for the daily Paid-Burst focus session. "
                "Use when the user clicks 'join paid-burst' or types 'join paid-burst' / 'paid-burst'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "notes": {
                        "type": "string",
                        "description": "Optional notes or target goals for this session.",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_leetcode",
            "description": (
                "Fetch today's LeetCode Daily Challenge: question number, title, "
                "difficulty, topics and the problem link. Use this whenever the user "
                "asks about the daily question, today's problem, its difficulty or topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_leetcode_activity",
            "description": (
                "Fetch the user's LeetCode stats: solved today, current streak and total "
                "active days. Use this for questions about the streak, consistency or "
                "whether a problem was solved today."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "LeetCode username. Optional; defaults to the configured LEETCODE_USERNAME.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_today_calendar_events",
            "description": (
                "Fetch today's Google Calendar events (time, summary, location). "
                "Use this when the user asks about their schedule, meetings or calendar."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_reminder",
            "description": (
                "Save a reminder so the user gets a WhatsApp ping when it is due. "
                "You MUST parse the task text and the due date/time out of the user's "
                "request, convert it to Asia/Kolkata (IST, UTC+5:30), and pass due_at as "
                "an ISO-8601 string with offset (e.g. 2026-09-14T17:00:00+05:30). "
                "After saving, confirm to the user what reminder was set and when."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The task detail the user wants to be reminded about.",
                    },
                    "due_at": {
                        "type": "string",
                        "description": "ISO-8601 datetime with a timezone offset, e.g. 2026-09-14T17:00:00+05:30.",
                    },
                },
                "required": ["text", "due_at"],
            },
        },
    },
]

_BASE_SYSTEM_PROMPT = """You are Bro-bot, the personal WhatsApp assistant, senior full-stack mentor, and growth accountability partner for Haricharan. \
You run on his private server and communicate exclusively over WhatsApp. \
You are built to push him to stay consistent, level up as a software engineer, and dominate his daily targets.

Your Core Pillars:
1. FULL-STACK MASTERY (MERN & SQL):
   - You are a seasoned full-stack engineer and database architect.
   - You provide daily MERN questions (React hooks/lifecycle, Node event loop/streams, MongoDB indexes/aggregation, Express pipelines) and daily SQL challenges (window functions, CTEs, self-joins, query optimization).
   - Review his answers and queries with sharp, practical feedback. Explain edge cases clearly.
   - Always format code snippets using WhatsApp monospace triple backticks (```javascript ... ``` or ```sql ... ```).

2. DAILY FOCUS SPRINTS ("PAID-BURST"):
   - Every morning at 9:00 AM, he receives a check-in message with an interactive button to "join paid-burst".
   - When he triggers "join paid-burst", call `checkin_paid_burst`, hype him up with high energy, celebrate his streak, and outline his daily grind (LeetCode + MERN + SQL).

3. GRIND & ALGORITHMS (LeetCode):
   - Remind him of the daily challenge, judge difficulty, give subtle hints without spoiling answers, track his streak, celebrate solves, and call him out if he is slacking.

4. TIME & SCHEDULE (Google Calendar):
   - Keep him ahead of his day by reviewing calendar events, meetings, and planning dedicated focus blocks.

5. MEMORY (Reminders):
   - Store tasks and pings accurately in MongoDB with timezone awareness.

STYLE:
- Casual, warm, razor-sharp, direct — an elite dev friend who talks straight. Use "bro".
- Short and scannable for WhatsApp (typically 3-6 lines). No corporate fluff, no long essays, no markdown tables.
- Use sparingly placed high-impact emojis (🔥, 🚀, 💡, ⚛️, 🗄️, 🎯).

TOOLS: Call function tools whenever you need live data or state mutations.
- get_daily_mern_question: get today's MERN challenge.
- get_daily_sql_question: get today's SQL challenge.
- evaluate_technical_answer: evaluate user's technical answer or query.
- checkin_paid_burst: record Paid-Burst checkin.
- get_daily_leetcode: today's problem info.
- get_leetcode_activity: streak and activity.
- get_today_calendar_events: Google Calendar events.
- save_reminder: schedule a reminder.

TIMEZONE RULES: Your configured timezone is {tz}. The current time is {now}. \
Interpret relative times in this timezone and convert to exact ISO-8601 with offset before saving reminders.
"""


def _build_system_prompt() -> str:
    now = datetime.now(TZ).strftime("%A, %d %b %Y, %I:%M %p")
    return _BASE_SYSTEM_PROMPT.format(tz=settings.SCHEDULER_TIMEZONE, now=now)


async def _execute_tool(name: str, args: dict) -> str:
    if name == "get_daily_mern_question":
        if args.get("generate_fresh"):
            q = await generate_ai_technical_question(topic="mern")
        else:
            q = get_daily_mern_question()
        return json.dumps({
            "formatted": format_mern_question_message(q),
            "details": q
        })

    if name == "get_daily_sql_question":
        if args.get("generate_fresh"):
            q = await generate_ai_technical_question(topic="sql")
        else:
            q = get_daily_sql_question()
        return json.dumps({
            "formatted": format_sql_question_message(q),
            "details": q
        })

    if name == "evaluate_technical_answer":
        category = args.get("category", "general")
        q_ctx = args.get("question_context", "")
        u_ans = args.get("user_answer", "")
        feedback = await evaluate_user_technical_answer(category, q_ctx, u_ans)
        return json.dumps({"feedback": feedback})

    if name == "checkin_paid_burst":
        notes = args.get("notes", "")
        result = record_paid_burst_checkin("Haricharan", notes=notes)
        stats = get_paid_burst_stats("Haricharan")
        return json.dumps({"checkin": result, "stats": stats})

    if name == "get_daily_leetcode":
        daily = await fetch_daily_question()
        return json.dumps({
            "date": daily["date"],
            "question_number": daily["question_number"],
            "title": daily["title"],
            "difficulty": daily["difficulty"],
            "topics": daily["topics"],
            "link": daily["link"],
        })

    if name == "get_leetcode_activity":
        username = args.get("username") or settings.LEETCODE_USERNAME
        if not username:
            return json.dumps({"error": "No LeetCode username configured or provided."})
        return json.dumps(await fetch_activity(username))

    if name == "get_today_calendar_events":
        events = fetch_daily_events()
        return json.dumps({
            "formatted": format_events_message(events),
            "events": events,
        })

    if name == "save_reminder":
        text = (args.get("text") or "").strip()
        due_at = (args.get("due_at") or "").strip()
        if not text or not due_at:
            return json.dumps({"error": "Both 'text' and 'due_at' are required."})
        try:
            parsed = datetime.fromisoformat(due_at)
        except ValueError:
            return json.dumps({"error": f"Could not parse due_at: {due_at}"})
        reminder = create_reminder(text, parsed)
        return json.dumps({"ok": True, "reminder": reminder})

    return json.dumps({"error": f"Unknown tool: {name}"})


async def generate_chat_response(user_text: str, user_id: str) -> str:
    prompt = user_text.strip()
    if not prompt:
        return "[Bot]: Please send a message."

    # Direct quick shortcuts
    lowered = prompt.lower()
    if lowered in ["join paid-burst", "paid-burst", "paid burst", "/burst"]:
        checkin = record_paid_burst_checkin("Haricharan")
        streak = checkin.get("streak", 1)
        status_txt = "🔥 *PAID-BURST ACTIVATED!* 🚀\n"
        if checkin.get("is_duplicate"):
            status_txt = f"⚡ *Already Locked In for Paid-Burst Today!* (Streak: {streak} days)\n"
        else:
            status_txt += f"Check-in locked at {checkin['time']}. Current Streak: *{streak} days* 💯\n\n"

        status_txt += (
            "🎯 *Today's Battle Plan:*\n"
            "1. ⚛️ *MERN*: Reply *mern* for today's question\n"
            "2. 🗄️ *SQL*: Reply *sql* for today's query challenge\n"
            "3. 🧠 *LeetCode*: Reply *leetcode* for daily problem\n\n"
            "Let's get this work done bro!"
        )
        return status_txt

    if lowered in ["mern", "/mern"]:
        q = get_daily_mern_question()
        return format_mern_question_message(q)

    if lowered in ["sql", "/sql"]:
        q = get_daily_sql_question()
        return format_sql_question_message(q)

    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": prompt},
    ]

    try:
        ai = get_ai_client()
        for _ in range(MAX_TOOL_ITERATIONS):
            response = ai.chat.completions.create(
                model="gemini-2.5-flash",
                messages=messages,
                tools=AGENT_TOOLS,
            )
            message = response.choices[0].message

            if not getattr(message, "tool_calls", None):
                answer = message.content
                if answer and answer.strip():
                    return answer.strip()
                break

            messages.append({
                "role": "assistant",
                "content": message.content or None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            })

            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                    result = await _execute_tool(tc.function.name, args)
                except Exception as e:
                    print(f"[tool error] {tc.function.name}: {e}")
                    result = json.dumps({"error": str(e)})
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
    except Exception as e:
        print(f"[llm error]: {e}")

    return "[Bot]: Sorry bro, I couldn't process that right now. Try again in a second!"
