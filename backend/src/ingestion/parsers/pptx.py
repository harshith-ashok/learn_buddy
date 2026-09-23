import io

from pptx import Presentation

from src.ingestion.schemas import ParsedDocument, ParsedSection


def parse(content: bytes) -> ParsedDocument:
    """Parse a PPTX into one flat, top-level section per slide.

    A slide's title placeholder (if any) becomes the section heading;
    every other shape with text is concatenated into the section body.
    """
    presentation = Presentation(io.BytesIO(content))
    sections: list[ParsedSection] = []

    for slide in presentation.slides:
        title_shape = slide.shapes.title
        title_text = title_shape.text.strip() if title_shape and title_shape.has_text_frame else None

        body_parts: list[str] = []
        for shape in slide.shapes:
            if shape is title_shape or not shape.has_text_frame:
                continue
            # `has_text_frame` above guarantees this at runtime, but it's a
            # plain bool, not a TypeGuard, so python-pptx's stub can't narrow
            # `shape` from the generic `BaseShape` that lacks `.text_frame`.
            text = shape.text_frame.text.strip()  # pyright: ignore[reportAttributeAccessIssue]
            if text:
                body_parts.append(text)

        body = "\n".join(body_parts)
        if not title_text and not body:
            continue

        sections.append(ParsedSection(heading=title_text or None, level=1, text=body, children=[]))

    title = sections[0].heading if sections and sections[0].heading else None
    return ParsedDocument(title=title, sections=sections)
