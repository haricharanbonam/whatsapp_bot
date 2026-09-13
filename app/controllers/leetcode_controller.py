from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.leetcode_service import fetch_activity, fetch_daily_question

router = APIRouter(prefix="/leetcode", tags=["LeetCode"])


class DailyQuestionResponse(BaseModel):
    date: str
    question_number: str
    title: str
    slug: str
    difficulty: str
    description: str
    examples: str
    topics: list[str]
    link: str
    user_status: Optional[str] = None


class ActivityResponse(BaseModel):
    username: str
    active_today: bool
    streak: int
    total_active_days: int


@router.get("/daily", response_model=DailyQuestionResponse)
async def get_daily_question():
    return await fetch_daily_question()


@router.get("/activity/{username}", response_model=ActivityResponse)
async def get_user_activity(username: str):
    return await fetch_activity(username)