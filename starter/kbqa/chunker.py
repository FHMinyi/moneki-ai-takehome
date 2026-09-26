"""Source-preserving chunks with separately mapped retrieval context."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

from .loader import Document

# Bump when parsing/layout semantics change; parameters also enter the cache key.
CHUNKER_VERSION = "chunker-3"
CHUNK_SIZE = 300
CHUNK_OVERLAP = 60
_HEADING = re.compile(r"^(#{1,6})\s+(.+)")
_SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*$")


@dataclass
class Chunk:
    doc_id: str
    chunk_id: str
    text: str  # Retrieval-only context + source; never a quote.
    source_text: str  # One exact slice of Document.text.
    heading: str = ""
    kind: str = "text"
    table_header: list[str] = field(default_factory=list)
    source_start: int = 0
    source_end: int = 0
    context_spans: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def layout_signature() -> list:
    return [CHUNKER_VERSION, CHUNK_SIZE, CHUNK_OVERLAP]


def _windows(text: str, start: int, end: int, table: bool):
    """Prefer paragraph/line boundaries; never split a table row.

    Size is a target: a single oversized table row stays intact. Only long
    prose lines need overlapping character windows. Every position is covered.
    """
    while start < end:
        stop = min(start + CHUNK_SIZE, end)
        overlap = 0
        if stop < end:
            boundary = text.rfind('\n\n', start, stop)
            if table or boundary < start:
                boundary = text.rfind('\n', start, stop)
                width = 1
            else:
                width = 2
            if boundary >= start:
                stop = boundary + width
            elif table:
                boundary = text.find('\n', stop, end)
                stop = boundary + 1 if boundary >= 0 else end
            else:
                overlap = min(CHUNK_OVERLAP, CHUNK_SIZE - 1)
        yield start, stop
        start = stop - overlap


def chunk_document(document: Document) -> list[Chunk]:
    text = document.text
    if not text:
        return []  # Metadata titles are not invented body evidence.
    lines = text.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    chunks: list[Chunk] = []
    headings: list[tuple[int, str, dict]] = []

    def span(a, b):
        return {'start': a, 'end': b, 'text': text[a:b]}

    def emit(a, b, table_header=None, header_span=None):
        context = [entry[2] for entry in headings]
        if header_span:
            context = context + [header_span]
        heading = ' > '.join([document.title] + [entry[1] for entry in headings])
        for start, end in _windows(text, a, b, table_header is not None):
            source = text[start:end]
            # Keep metadata title explicitly separate from body-mapped context.
            prefix = [document.title] if document.title else []
            prefix += [s['text'].strip() for s in context if not (start <= s['start'] and s['end'] <= end)]
            chunks.append(Chunk(
                document.doc_id, f'{document.doc_id}#{len(chunks) + 1}',
                '\n'.join(prefix + [source]), source, heading,
                'table' if table_header is not None else 'text', table_header or [],
                start, end, list(context),
            ))

    i = 0
    while i < len(lines):
        match = _HEADING.match(lines[i]) if document.fmt in ('md', 'markdown') else None
        if match:
            level = len(match[1])
            headings = [entry for entry in headings if entry[0] < level]
            headings.append((level, match[2].strip(), span(offsets[i], offsets[i+1])))
            emit(offsets[i], offsets[i+1])
            i += 1
        elif i + 1 < len(lines) and '|' in lines[i] and _SEPARATOR.fullmatch(lines[i+1].strip()):
            j = i + 2
            while j < len(lines) and '|' in lines[j] and lines[j].strip():
                j += 1
            header = [cell.strip() for cell in lines[i].strip().strip('|').split('|')]
            emit(offsets[i], offsets[j], header, span(offsets[i], offsets[i+2]))
            i = j
        else:
            j = i + 1
            while j < len(lines):
                if document.fmt in ('md', 'markdown') and _HEADING.match(lines[j]):
                    break
                if j + 1 < len(lines) and '|' in lines[j] and _SEPARATOR.fullmatch(lines[j+1].strip()):
                    break
                j += 1
            emit(offsets[i], offsets[j])
            i = j
    return chunks


def chunk_documents(documents: list[Document]) -> list[Chunk]:
    return [chunk for document in documents for chunk in chunk_document(document)]
