import json
from datetime import date, datetime, timezone

import httpx
from fastapi import HTTPException

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
LEETCODE_TIMEOUT_SECONDS = 10.0

DAILY_QUERY = """
query questionOfToday {
  activeDailyCodingChallengeQuestion {
    date
    link
    userStatus
    question {
      questionFrontendId
      title
      titleSlug
      difficulty
      content
      exampleTestcases
      topicTags {
        name
        slug
      }
    }
  }
}
"""

CALENDAR_QUERY = """
query userProfileCalendar($username: String!, $year: Int) {
  matchedUser(username: $username) {
    userCalendar(year: $year) {
      activeYears
      streak
      totalActiveDays
      submissionCalendar
    }
  }
}
"""


async def leetcode_graphql(query: str, variables: dict) -> dict:
    payload = {"query": query, "variables": variables}
    try:
        async with httpx.AsyncClient(timeout=LEETCODE_TIMEOUT_SECONDS) as client:
            response = await client.post(LEETCODE_GRAPHQL_URL, json=payload)
    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="LeetCode is temporarily unreachable, please try again later.",
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"LeetCode responded with HTTP {response.status_code}.",
        )

    try:
        body = response.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Invalid response from LeetCode.")

    if body.get("errors"):
        for error in body["errors"]:
            if "does not exist" in str(error.get("message", "")).lower():
                raise HTTPException(status_code=404, detail="LeetCode user not found.")
        raise HTTPException(
            status_code=502,
            detail=f"LeetCode GraphQL error: {body['errors']}",
        )

    return body.get("data") or {}


async def fetch_daily_question() -> dict:
    data = await leetcode_graphql(DAILY_QUERY, {})
    daily = data.get("activeDailyCodingChallengeQuestion")
    if not daily:
        raise HTTPException(
            status_code=503,
            detail="Today's daily challenge is unavailable right now.",
        )

    question = daily.get("question") or {}
    link = daily.get("link") or ""
    topics = [
        topic.get("name")
        for topic in question.get("topicTags", [])
        if topic.get("name")
    ]

    return {
        "date": daily.get("date"),
        "question_number": question.get("questionFrontendId"),
        "title": question.get("title"),
        "slug": question.get("titleSlug"),
        "difficulty": question.get("difficulty"),
        "description": question.get("content"),
        "examples": question.get("exampleTestcases"),
        "topics": topics,
        "link": f"https://leetcode.com{link}" if link else "",
        "user_status": daily.get("userStatus"),
    }


def _is_active_today(submission_calendar: str, today: date) -> bool:
    if not submission_calendar:
        return False

    try:
        calendar = json.loads(submission_calendar)
    except (TypeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=502,
            detail="Malformed submission calendar data returned by LeetCode.",
        )

    if not isinstance(calendar, dict):
        raise HTTPException(
            status_code=502,
            detail="Malformed submission calendar data returned by LeetCode.",
        )

    for timestamp, count in calendar.items():
        try:
            submission_day = datetime.fromtimestamp(
                int(timestamp), tz=timezone.utc
            ).date()
        except (ValueError, OSError, OverflowError):
            continue
        if submission_day == today and int(count) > 0:
            return True
    return False


async def fetch_activity(username: str) -> dict:
    today = datetime.now(timezone.utc).date()
    data = await leetcode_graphql(
        CALENDAR_QUERY, {"username": username, "year": today.year}
    )

    matched = data.get("matchedUser")
    if not matched:
        raise HTTPException(
            status_code=404,
            detail=f"LeetCode user '{username}' not found.",
        )

    calendar = matched.get("userCalendar")
    if not calendar:
        raise HTTPException(
            status_code=404,
            detail=f"No calendar data found for LeetCode user '{username}'.",
        )

    active_today = _is_active_today(calendar.get("submissionCalendar"), today)

    return {
        "username": username,
        "active_today": active_today,
        "streak": int(calendar.get("streak") or 0),
        "total_active_days": int(calendar.get("totalActiveDays") or 0),
    }