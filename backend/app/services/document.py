from __future__ import annotations

import hashlib
import io
from pathlib import Path
import re
from uuid import UUID

import magic
from docx import Document
from fastapi import HTTPException, status
import nltk
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from nltk.tokenize import sent_tokenize
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_section import DocumentSection

nltk.download('punkt_tab')

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

def join_broken_sentences(text: str) -> str:
    # Replace newline followed by lowercase letter (continuation) with space
    text = re.sub(r'\n(?=[a-z])', ' ', text)
    # Also handle cases where line ends with a hyphenated word
    text = re.sub(r'-\n', '', text)
    return text

def chunk_and_embed(sections: list[dict], threshold: float = 0.35) -> list[dict]:
    chunks: list[dict] = []

    min_sentences = 2
    max_sentences = 7
    min_chars = 220
    max_chars = 1200

    def _is_list_item(line: str) -> bool:
        stripped = line.strip()
        if not stripped:
            return False

        bullet_prefixes = ("-", "*", "•", "‣", "◦", "▪")
        if stripped.startswith(bullet_prefixes):
            return True

        if len(stripped) >= 3 and stripped[0].isdigit():
            sep_idx = 1
            while sep_idx < len(stripped) and stripped[sep_idx].isdigit():
                sep_idx += 1
            if sep_idx < len(stripped) and stripped[sep_idx] in (".", ")", "]"):
                return True

        return False

    def _split_structural_blocks(text: str) -> list[tuple[str, str]]:
        lines = text.splitlines()
        blocks: list[tuple[str, str]] = []

        current_lines: list[str] = []
        current_kind: str | None = None

        def _flush() -> None:
            nonlocal current_lines, current_kind
            if not current_lines:
                return
            block_text = "\n".join(current_lines).strip()
            if block_text:
                blocks.append((current_kind or "text", block_text))
            current_lines = []
            current_kind = None

        for line in lines:
            stripped = line.strip()
            if not stripped:
                _flush()
                continue

            kind = "list" if _is_list_item(stripped) else "text"
            if current_kind is None:
                current_kind = kind
            elif current_kind != kind:
                _flush()
                current_kind = kind

            current_lines.append(line)

        _flush()

        if not blocks:
            single = text.strip()
            return [("text", single)] if single else []

        return blocks

    def _append_chunk(section: dict, content: str) -> None:
        cleaned = content.strip()
        if not cleaned:
            return
        chunks.append(
            {
                "content": cleaned,
                "source_page": section.get("source_page"),
                "source_page_end": section.get("source_page_end"),
                "source_identifier": section.get("source_identifier"),
                "document_type": section.get("document_type"),
                "embedding": None,
            }
        )

    def _semantic_split(text: str, similarity_cutoff: float) -> list[str]:
        sentences: list[str] = sent_tokenize(text, language="english")
        if len(sentences) <= 1:
            return [text]

        embeddings = _model.encode(sentences)
        similarities = [
            cosine_similarity([embeddings[i]], [embeddings[i + 1]])[0][0]
            for i in range(len(embeddings) - 1)
        ]

        if similarities:
            adaptive_cutoff = min(similarity_cutoff, float(np.percentile(similarities, 20)))
        else:
            adaptive_cutoff = similarity_cutoff

        sentence_groups: list[list[str]] = []
        current_group: list[str] = [sentences[0]]

        for i, sim in enumerate(similarities):
            current_len = len(" ".join(current_group))
            should_split_semantic = (
                sim < adaptive_cutoff
                and len(current_group) >= min_sentences
                and current_len >= min_chars
            )
            should_split_size = (
                len(current_group) >= max_sentences
                or current_len >= max_chars
            )

            if should_split_semantic or should_split_size:
                sentence_groups.append(current_group)
                current_group = [sentences[i + 1]]
            else:
                current_group.append(sentences[i + 1])

        if current_group:
            sentence_groups.append(current_group)

        merged_groups: list[list[str]] = []
        for group in sentence_groups:
            group_text = " ".join(group)
            if merged_groups and (
                len(group_text) < (min_chars // 2) or len(group) < min_sentences
            ):
                merged_groups[-1].extend(group)
            else:
                merged_groups.append(group)

        return [" ".join(group).strip() for group in merged_groups if " ".join(group).strip()]

    for section in sections:
        text = (section.get("content") or "").strip()
        text = join_broken_sentences(text)
        if not text:
            continue

        blocks = _split_structural_blocks(text)

        for block_kind, block_text in blocks:
            block_sentences = sent_tokenize(block_text, language="english")
            block_is_short = len(block_text) < max_chars and len(block_sentences) <= 3

            if block_kind == "list" and len(block_text) <= int(max_chars * 1.25):
                _append_chunk(section, block_text)
                continue

            if block_is_short:
                _append_chunk(section, block_text)
                continue

            for split_text in _semantic_split(block_text, threshold):
                _append_chunk(section, split_text)

    if chunks:
        texts = [c["content"] for c in chunks]
        embeddings_batch = _model.encode(texts)
        for chunk, embedding in zip(chunks, embeddings_batch):
            chunk["embedding"] = embedding.tolist()

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