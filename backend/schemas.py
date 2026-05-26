"""
Pydantic schemas for request validation and response serialization.
Separating schemas from ORM models keeps the API contract explicit.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr


# ─── Auth ────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_email: str


# ─── Flashcards ──────────────────────────────────────────────────────────────

class FlashcardOut(BaseModel):
    id: int
    front: str
    back: str

    model_config = {"from_attributes": True}


# ─── Quiz ────────────────────────────────────────────────────────────────────

class QuizQuestionOut(BaseModel):
    id: int
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer_index: int

    model_config = {"from_attributes": True}


# ─── Documents ───────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    filename: str
    upload_timestamp: datetime
    flashcard_count: int = 0
    quiz_question_count: int = 0

    model_config = {"from_attributes": True}


class DocumentDetailOut(BaseModel):
    id: int
    filename: str
    upload_timestamp: datetime
    extracted_text: str
    flashcards: List[FlashcardOut] = []
    quiz_questions: List[QuizQuestionOut] = []

    model_config = {"from_attributes": True}


# ─── Generation ──────────────────────────────────────────────────────────────

class GenerationResponse(BaseModel):
    flashcards: List[FlashcardOut]
    quiz_questions: List[QuizQuestionOut]
    message: str = "Generation complete"
