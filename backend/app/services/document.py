from __future__ import annotations

import hashlib
import io
from pathlib import Path
from uuid import UUID

import magic
from docx import Document
from fastapi import HTTPException, status
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_section import DocumentSection


_model = SentenceTransformer("all-MiniLM-L6-v2")
_ALLOWED_MIME_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
}


def validate_file_type(file_bytes: bytes, filename: str) -> str:
    mime_type = magic.from_buffer(file_bytes[:8], mime=True)
    doc_type = _ALLOWED_MIME_TYPES.get(mime_type)
    if doc_type is None:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Accepted formats: PDF, DOCX, TXT",
        )
    return doc_type


def compute_document_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def extract_text_by_type(file_bytes: bytes, doc_type: str) -> list[dict]:
    if doc_type == "pdf":
        return extract_from_pdf(file_bytes)
    if doc_type == "docx":
        return extract_from_docx(file_bytes)
    if doc_type == "txt":
        return extract_from_txt(file_bytes)
    raise ValueError(f"Unsupported document type: {doc_type}")


def extract_from_pdf(file_bytes: bytes) -> list[dict]:
    reader = PdfReader(io.BytesIO(file_bytes))
    sections: list[dict] = []

    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        if not page_text.strip():
            continue
        sections.append(
            {
                "content": page_text,
                "source_page": page_num,
                "source_page_end": page_num,
                "source_identifier": f"Page {page_num}",
                "document_type": "pdf",
            }
        )

    return sections


def extract_from_docx(file_bytes: bytes) -> list[dict]:
    doc = Document(io.BytesIO(file_bytes))
    sections: list[dict] = []

    for para_index, para in enumerate(doc.paragraphs, start=1):
        if not para.text.strip():
            continue
        sections.append(
            {
                "content": para.text,
                "source_page": None,
                "source_page_end": None,
                "source_identifier": f"Paragraph {para_index}",
                "document_type": "docx",
            }
        )

    return sections


def extract_from_txt(file_bytes: bytes) -> list[dict]:
    text = file_bytes.decode("utf-8")
    paragraphs = text.split("\n\n")
    sections: list[dict] = []
    current_line = 1

    for paragraph in paragraphs:
        paragraph_text = paragraph.strip()
        if not paragraph_text:
            continue

        paragraph_lines = paragraph_text.splitlines() or [paragraph_text]
        start_line = current_line
        end_line = start_line + len(paragraph_lines) - 1
        sections.append(
            {
                "content": paragraph_text,
                "source_page": None,
                "source_page_end": None,
                "source_identifier": f"Lines {start_line}-{end_line}",
                "document_type": "txt",
            }
        )
        current_line = end_line + 2

    return sections


def chunk_and_embed(sections: list[dict]) -> list[dict]:
    chunks: list[dict] = []

    for section in sections:
        content = section["content"]
        if len(content) <= 500:
            chunks.append(section.copy())
            continue

        start = 0
        while start < len(content):
            end = min(start + 400, len(content))
            chunk = section.copy()
            chunk["content"] = content[start:end]
            chunks.append(chunk)
            if end >= len(content):
                break
            start = end - 50

    if not chunks:
        return []

    embeddings = _model.encode([chunk["content"] for chunk in chunks])
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = [float(value) for value in embedding]

    return chunks


async def save_sections_to_db(chunks: list[dict], session_id: UUID, db: AsyncSession) -> None:
    document_sections = [
        DocumentSection(
            session_id=session_id,
            section_index=index,
            content=chunk["content"],
            embedding=chunk["embedding"],
            source_page=chunk["source_page"],
            source_page_end=chunk["source_page_end"],
            source_identifier=chunk["source_identifier"],
            document_type=chunk["document_type"],
        )
        for index, chunk in enumerate(chunks)
    ]

    db.add_all(document_sections)
    await db.commit()
