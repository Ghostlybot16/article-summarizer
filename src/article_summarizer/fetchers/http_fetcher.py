"""
HTTP article fetcher. 

Responsibility:
- Given a URL, download the page, extract main text + metadata, 
and return an Article value object.


Implementation details:
- Uses `trafilatura` for article extraction.
- Normalizes metadata (title, authors, language, site name).
- Parses published date to a timezone-aware UTC datetime when possible. 

Notes:
- Heavy cleaning is not done here. It belongs to the Preprocessor.
- This fetcher is domain-agnostic (works for by-laws, news, blog posts, if they are HTML).
  PDFs will be handled by a different fetcher.

"""

from __future__ import annotations

from datetime import datetime, timezone
from encodings import raw_unicode_escape
from hashlib import sha1
from typing import Any, Optional, Tuple

import trafilatura
from dateparser import parse as parse_date

from ..core.models import Article


def _make_id(url: str) -> str:
    """Stable ID for an article: sha1 of the URL."""
    return sha1(url.encode("utf-8")).hexdigest()


def _to_tuple_str(x: Any) -> Tuple[str, ...]:
    """Conversion of metadata 'authors' into an immutable tuple of strings."""
    if not x:
        return tuple()
    if isinstance(x, (list, tuple)):
        return tuple(str(i).strip() for i in x if i)
    return (str(x).strip(),)


def _parse_published(dt_str: Optional[str]) -> Optional[datetime]:
    """
    Parse a date string (ISO or fuzzy) into a timezone-aware UTC datetime.
    Returns None if parsing fails
    """
    if not dt_str:
        return None
    try:
        dt = parse_date(dt_str, settings={"RETURN_AS_TIMEZONE_AWARE": True})
        if not dt:
            return None
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


class HttpArticleFetcher:
    """
    Fetcher that retrieves an article from a given HTTP(S) URL using trafilatura.
    
    Usage:
        fetcher = HttpArticleFetcher()
        article = fetcher.fetch("https://example.com/some-article")
    """
    
    def __init__(
        self, 
        *, 
        min_chars: int = 200,
    ) -> None:
        """
        Args:
            min_chars: Minimum number of characters required in extracted text to accept it.
        """
        self.min_chars = min_chars
    
    
    def fetch(self, input_ref: str) -> Article:
        """
        Download and extract the main content & metadata from a URL.
        
        Args:
            input_ref: HTTP(S) URL string. 
        
        Returns:
            Article: value object with text and metadata.
        
        Raises:
            RuntimeError: if the content cannot be downloaded or extracted.
        """
        
        url = input_ref.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            raise RuntimeError(
                f"HttpArticleFetcher only supports HTTP(S) URLs, got: {url!r}"
            )
        
        
        # Download the page (HTML as string), trafilatura handles basic retries. 
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            raise RuntimeError(f"Failed to download content from: {url}")
        
        
        # Extract text and metadata.
        # extract_metadata returns keys like: title, authors, date, language, sitename, description
        meta = trafilatura.extract_metadata(downloaded) or None
                
        text = trafilatura.extract(
            downloaded, 
            include_tables=False,
            include_comments=False,
            favor_recall=True,
        ) or ""
        
        def _meta_get(obj, attr: str):
            """Safely get metadata by attribute name from dict or object, else None."""
            if obj is None:
                return None
            if isinstance(obj, dict):
                return obj.get(attr)
            return getattr(obj, attr, None)

         
        clean_text = text.strip()
        if not clean_text:
            raise RuntimeError(f"Extraction produced empty text for: {url}")
        if len(clean_text) < self.min_chars:
            raise RuntimeError(
                f"Extraction too short ({len(clean_text)} chars) for: {url}"
            )
        
        # Normalize metadata fields (support dict or object)
        raw_title = _meta_get(meta, "title")
        raw_authors = _meta_get(meta, "authors")
        raw_date = _meta_get(meta, "date")
        raw_lang = _meta_get(meta, "language")
        raw_site = _meta_get(meta, "sitename")
        raw_desc = _meta_get(meta, "description")
        
        # Normalize metadata fields
        title = (raw_title or None) and str(raw_title).strip()
        authors = _to_tuple_str(raw_authors)
        published = _parse_published(raw_date)
        lang = (raw_lang or None) and str(raw_lang).strip()
        source = (raw_site or None) and str(raw_site).strip()
        
        
        # Build Article 
        return Article(
            id=_make_id(url),
            url=url,
            title=title,
            authors=authors,
            published=published,
            text=clean_text,
            lang=lang,
            source=source,
            extra={
                "description": (raw_desc or None),
                "meta_raw_type": type(meta).__name__ if meta is not None else None,
            },
        )