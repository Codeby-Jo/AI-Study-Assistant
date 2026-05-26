"""
Documents router — upload, list, get, delete.
All endpoints require a valid JWT (get_current_user dependency).
All queries are scoped to the authenticated user's ID — data isolation.
"""

import io
import tempfile
import os

import fitz  # PyMuPDF
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import Document, User
from backend.schemas import DocumentDetailOut, DocumentOut

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {"application/pdf", "text/plain"}
ALLOWED_EXTENSIONS = {".pdf", ".txt"}
MAX_FILE_SIZE_MB = 20


def _extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    doc.close()
    text = "\n".join(pages).strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract any text from this PDF. It may be scanned or image-only.",
        )
    return text


def _extract_text_from_txt(file_bytes: bytes) -> str:
    """Decode plain text file content."""
    try:
        return file_bytes.decode("utf-8").strip()
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1").strip()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Upload a PDF or .txt file.
    Extracts text and stores it in the database. Original file is not stored.
    """
    filename = file.filename or "upload"
    ext = os.path.splitext(filename)[-1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{ext}'. Only .pdf and .txt files are accepted.",
        )

    content = await file.read()

    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large ({size_mb:.1f} MB). Maximum allowed is {MAX_FILE_SIZE_MB} MB.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    if ext == ".pdf":
        extracted_text = _extract_text_from_pdf(content)
    else:
        extracted_text = _extract_text_from_txt(content)

    if len(extracted_text.strip()) < 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Extracted text is too short to generate study material.",
        )

    doc = Document(
        user_id=current_user.id,
        filename=filename,
        extracted_text=extracted_text,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return DocumentOut(
        id=doc.id,
        filename=doc.filename,
        upload_timestamp=doc.upload_timestamp,
        flashcard_count=0,
        quiz_question_count=0,
    )


@router.get("", response_model=list[DocumentOut])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all documents belonging to the authenticated user.
    Scoped to current_user.id — users cannot see each other's documents.
    """
    docs = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.upload_timestamp.desc())
        .all()
    )
    return [
        DocumentOut(
            id=d.id,
            filename=d.filename,
            upload_timestamp=d.upload_timestamp,
            flashcard_count=len(d.flashcards),
            quiz_question_count=len(d.quiz_questions),
        )
        for d in docs
    ]


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get a single document with its flashcards and quiz questions.
    Returns 404 if the document doesn't exist or belongs to another user.
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a document and all its flashcards and quiz questions (cascade).
    Returns 404 if the document doesn't exist or belongs to another user.
    """
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == current_user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    db.delete(doc)
    db.commit()
