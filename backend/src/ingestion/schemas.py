from pydantic import BaseModel, Field


class ParsedSection(BaseModel):
    """One node in a document's heading tree.

    `heading=None` marks a section with no detected heading (e.g. the lead
    text before the first heading, or a whole-document fallback for
    formats without structural markup).
    """

    heading: str | None
    level: int
    text: str
    children: list["ParsedSection"] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    """Format-normalized output of every parser in `ingestion.parsers`."""

    title: str | None
    sections: list[ParsedSection]


class Chunk(BaseModel):
    """One retrieval unit produced by `ingestion.chunker.chunk_document`."""

    order: int
    section_heading: str | None
    text: str
    token_count: int


class ExtractedTopic(BaseModel):
    """One topic as emitted by the classification model, pre-persistence.

    `prerequisites` and `subtopics` reference other topics/subtopics by
    `name` within the same extraction result — `topic_extractor` resolves
    those names to row ids when writing to Postgres.
    """

    name: str
    description: str
    subtopics: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class TopicExtractionResult(BaseModel):
    """The full structured response the topic-extraction prompt must emit."""

    topics: list[ExtractedTopic]
