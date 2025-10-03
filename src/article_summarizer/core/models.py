"""
Core value objects used in the summarization pipeline.
Keeps text and metadata structured in a clean, immutable way.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Tuple, Optional


@dataclass(frozen=True, slots=True)
class Article:
    """
    Represents a single source document (by-law text, news article, etc)
    
    This object should contain the best available textual content with helpful metadata. 
    It is designed to be created by a Fetcher (HTTP, RSS, PDF fetcher), optionally refined by a Preprocessor and then consumed by a Summarizer.
    
    Attributes:
        id: 
            Stable identifier for this article. Common options:
            - sha1(url) for web content, 
            - a UUID for local/PDF sources
        url: 
            Source locator. Use an HTTP(S) URL for web content, or a `file://` URI for local files (eg. extracted PDFs).
        title: 
            Best-effort title (may be None if not detectable).
        authors: 
            Immutable collection of author names, if known.
        published: 
            Publication timestamp if known. 
        text: 
            The article body text. This should be processed, not raw HTML.
        lang: 
            ISO language code (eg. 'en'), if detected 
        source: 
            Human-readable source label (eg. "City of Toronto", "BBC News").
        extra: 
            miscellaneous metadata
    """
    # Identity and origin
    id: str                                              
    url: str                                             
    
    # Human readable metadata
    title: Optional[str]                                 
    authors: Tuple[str, ...]                                  
    
    # Timing
    published: Optional[datetime]                        
    
    # Content
    text: str                                            
    
    # Optional metadata
    lang: Optional[str] = None                           
    source: Optional[str] = None                         
    extra: dict[str, Any] = field(default_factory=dict)  

@dataclass(frozen=True, slots=True)
class Summary:
    """
    Represents the output of summarization for a single Article.
    
    Attributes:
        article_id: 
            Foreign key linking back to the source Article.id
        strategy: 
            Identifier of the strategy used to summarize
        text: 
            The final, human-readable summary text.
        sentences: 
            For extractive methods, the sentence-level selections. For abstractive methods, this can be empty or a heuristic split
        meta: 
            Free-form metrics/parameters (eg. input length, model name, scores) 
        created_at: 
            UTC timestamp when the summary was produced, timezone-aware.
    """
    # Link to source 
    article_id: str
    
    strategy: str
    
    # Output content
    text: str
    sentences: list[str] = field(default_factory=list)
    
    # Meta data 
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )