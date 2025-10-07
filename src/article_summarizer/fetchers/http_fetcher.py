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
  PDFs will be handles by a different fetcher.

"""

from __future__ import annotations

from datetime import datetime, timezone
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
        timeout: int = 15, 
        user_agent: Optional[str] = None, 
        min_chars: int = 200,
    ) -> None:
        """
        Args:
            timeout: Network timeout in seconds used by trafilatura's downloader.
            user_agent: Optional custom user-agent. If none, trafilatura default is used.
            min_chars: Minimum number of characters required in extracted text to accept it.
        """
        self.timeout = timeout
        self.user_agent = user_agent
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
        downloaded = trafilatura.fetch_url(
            url,
            timeout=self.timeout,
            user_agent=self.user_agent,            
        )
        if not downloaded:
            raise RuntimeError(f"Failed to downloaded content from: {url}")
        
        
        # Extract text and metadata.
        # extract_metadata returns keys like: title, authors, date, language, sitename, description
        meta = trafilatura.extract_metadata(downloaded, url=url) or {}
        text = trafilatura.extract(
            downloaded, 
            include_tables=False,
            include_comments=False,
            favor_recall=True,
        ) or ""
        
        clean_text = text.strip()
        if not clean_text:
            raise RuntimeError(f"Extracted produced empty text for: {url}")
        if len(clean_text) < self.min_chars:
            raise RuntimeError(
                f"Extraction too short ({len(clean_text)} chars) for: {url}"
            )
        
        
        # Normalize metadata fields
        title = (meta.get("title") or None) and str(meta.get("title")).strip()
        authors = _to_tuple_str(meta.get("authors"))
        published = _parse_published(meta.get("date"))
        lang = (meta.get("language") or None) and str(meta.get("language")).strip()
        source = (meta.get("sitename") or None) and str(meta.get("sitename")).strip()
        
        
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
                "description": meta.get("description"),
                "meta_raw": meta,
            },
        )