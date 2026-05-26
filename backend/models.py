"""
SQLAlchemy ORM models for the Study Assistant application.

Tables:
  - users          (id, email, hashed_password, created_at)
  - documents      (id, user_id FK, filename, extracted_text, upload_timestamp)
  - flashcards     (id, document_id FK, front, back)
  - quiz_questions (id, document_id FK, question, option_a/b/c/d, correct_answer_index)

All child tables use cascade delete so removing a document also removes
its flashcards and quiz questions automatically.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    documents = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    extracted_text = Column(Text, nullable=False)
    upload_timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="documents")
    flashcards = relationship(
        "Flashcard",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    quiz_questions = relationship(
        "QuizQuestion",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)

    document = relationship("Document", back_populates="flashcards")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    question = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_answer_index = Column(Integer, nullable=False)  # 0=A, 1=B, 2=C, 3=D

    document = relationship("Document", back_populates="quiz_questions")
