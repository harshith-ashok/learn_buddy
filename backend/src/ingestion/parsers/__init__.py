from pathlib import Path

from src.core.errors import AppError
from src.ingestion.parsers import docx as docx_parser
from src.ingestion.parsers import pdf as pdf_parser
from src.ingestion.parsers import pptx as pptx_parser
from src.ingestion.schemas import ParsedDocument

_PARSERS_BY_EXTENSION = {
    ".pdf": pdf_parser.parse,
    ".docx": docx_parser.parse,
    ".pptx": pptx_parser.parse,
}

SUPPORTED_EXTENSIONS = tuple(_PARSERS_BY_EXTENSION)


class UnsupportedDocumentFormatError(AppError):
    def __init__(self, filename: str) -> None:
        super().__init__(
            code="unsupported_media_type",
            message=f"Unsupported document format for '{filename}'; expected one of {SUPPORTED_EXTENSIONS}",
            status_code=415,
        )


def parse_document(filename: str, content: bytes) -> ParsedDocument:
    """Dispatch to the parser for `filename`'s extension."""
    extension = Path(filename).suffix.lower()
    parser = _PARSERS_BY_EXTENSION.get(extension)
    if parser is None:
        raise UnsupportedDocumentFormatError(filename)
    return parser(content)
