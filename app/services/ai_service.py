import json
from datetime import datetime
from zoneinfo import ZoneInfo

from openai import OpenAI

from app.core.config import settings
from app.services.leetcode_service import fetch_daily_question, fetch_activity
from app.integrations.calendar import fetch_daily_events, format_events_message
from app.integrations.reminders import create_reminder

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=settings.AI_API_KEY,
)

TZ = ZoneInfo(settings.SCHEDULER_TIMEZONE)
MAX_TOOL_ITERATIONS = 3

AGENT_TOOLS = [
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

_BASE_SYSTEM_PROMPT = """You are Bro-bot, the personal WhatsApp assistant for Haricharan. \
You run on his private EC2 server and are reached only through WhatsApp. You are his \
accountability partner for growth — built to keep him consistent, improving and motivated. \
Your job has three pillars:

1. Grind — LeetCode. Remind him of the daily challenge, judge how hard today's question \
looks, track his streak, celebrate solves and lovingly call him out when he slacks.
2. Time — his Google Calendar. Answer questions about his schedule and help him plan the day.
3. Memory — reminders. He tells you things to remember and you save them so he gets a \
WhatsApp ping at the right moment.

STYLE: casual, warm, direct — a good friend who talks straight. Use "bro". Keep replies short \
and scannable for WhatsApp (2-4 lines usually, never more than 6). Sparing emojis. No \
corporate fluff, no essays, no markdown tables.

TOOLS: You have function tools. Whenever the user's question needs live data you do not have \
in context, call the right tool instead of guessing or making things up:
- get_daily_leetcode — today's daily challenge (difficulty, topics, link).
- get_leetcode_activity — his streak / whether he solved today (LEETCODE_USERNAME default).
- get_today_calendar_events — today's schedule from his Google Calendar.
- save_reminder — store a reminder he asks for.

TIMEZONE RULES (critical): Your configured timezone is {tz}. The current time is {now}. \
Always interpret relative times ("5pm today", "tomorrow 9am", "in 30 minutes") in that \
timezone and convert them to an exact timestamp before saving a reminder.
"""


def _build_system_prompt() -> str:
    now = datetime.now(TZ).strftime("%A, %d %b %Y, %I:%M %p")
    return _BASE_SYSTEM_PROMPT.format(tz=settings.SCHEDULER_TIMEZONE, now=now)


async def _execute_tool(name: str, args: dict) -> str:
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

    messages: list[dict] = [
        {"role": "system", "content": _build_system_prompt()},
        {"role": "user", "content": prompt},
    ]

    try:
        for _ in range(MAX_TOOL_ITERATIONS):
            response = client.chat.completions.create(
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

    return "[Bot]: Sorry, I couldn't generate a response right now."