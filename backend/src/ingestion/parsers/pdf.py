import io

from pypdf import PdfReader

from src.ingestion.schemas import ParsedDocument, ParsedSection

_MAX_HEADING_LEN = 80
_HEADING_TERMINATORS = (".", ",", ";")


def _split_heading(page_text: str) -> tuple[str | None, str]:
    """Best-effort split of a page's leading line into `(heading, body)`.

    PDF text extraction carries no font/style metadata via `pypdf`, so
    headings can't be detected reliably. A short first line that doesn't
    read like the start of a sentence is treated as one; anything else
    keeps the whole page as heading-less body text.
    """
    lines = page_text.splitlines()
    if not lines:
        return None, ""

    first_line = lines[0].strip()
    rest = "\n".join(lines[1:]).strip()

    looks_like_heading = (
        first_line
        and len(first_line) <= _MAX_HEADING_LEN
        and not first_line.endswith(_HEADING_TERMINATORS)
        and rest
    )
    if looks_like_heading:
        return first_line, rest
    return None, page_text.strip()


def parse(content: bytes) -> ParsedDocument:
    """Parse a PDF into one flat, top-level section per page.

    No cross-page heading hierarchy is attempted — see `_split_heading`.
    """
    reader = PdfReader(io.BytesIO(content))
    sections: list[ParsedSection] = []

    for page in reader.pages:
        page_text = (page.extract_text() or "").strip()
        if not page_text:
            continue
        heading, body = _split_heading(page_text)
        sections.append(ParsedSection(heading=heading, level=1, text=body, children=[]))

    title = reader.metadata.title if reader.metadata else None
    return ParsedDocument(title=title, sections=sections)
