"""
Generation router — trigger LLM generation and retrieve results.
All endpoints require a valid JWT.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.llm import generate_study_content
from backend.models import Document, Flashcard, QuizQuestion, User
from backend.schemas import FlashcardOut, GenerationResponse, QuizQuestionOut

router = APIRouter(prefix="/documents", tags=["generation"])


@router.post("/{document_id}/generate", response_model=GenerationResponse)
async def generate_content(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate flashcards and quiz questions for a document using an LLM.
    Deletes any previously generated content for this document before inserting new.
    Returns 404 if document doesn't exist or belongs to another user.
    Returns 503 if the LLM call fails.
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    # Call the LLM
    try:
        data = await generate_study_content(doc.extracted_text)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )

    # Clear any previously generated content
    db.query(Flashcard).filter(Flashcard.document_id == document_id).delete()
    db.query(QuizQuestion).filter(QuizQuestion.document_id == document_id).delete()

    # Persist flashcards
    new_flashcards = []
    for fc in data.get("flashcards", []):
        obj = Flashcard(
            document_id=document_id,
            front=fc["front"],
            back=fc["back"],
        )
        db.add(obj)
        new_flashcards.append(obj)

    # Persist quiz questions
    new_quiz = []
    for q in data.get("quiz", []):
        opts = q["options"]
        obj = QuizQuestion(
            document_id=document_id,
            question=q["question"],
            option_a=opts[0],
            option_b=opts[1],
            option_c=opts[2],
            option_d=opts[3],
            correct_answer_index=q["correct_answer_index"],
        )
        db.add(obj)
        new_quiz.append(obj)

    db.commit()

    # Refresh to get IDs
    for obj in new_flashcards + new_quiz:
        db.refresh(obj)

    return GenerationResponse(
        flashcards=[FlashcardOut.model_validate(f) for f in new_flashcards],
        quiz_questions=[QuizQuestionOut.model_validate(q) for q in new_quiz],
    )


@router.get("/{document_id}/flashcards", response_model=list[FlashcardOut])
def get_flashcards(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve saved flashcards for a document (scoped to current user)."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return doc.flashcards


@router.get("/{document_id}/quiz", response_model=list[QuizQuestionOut])
def get_quiz(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve saved quiz questions for a document (scoped to current user)."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return doc.quiz_questions
