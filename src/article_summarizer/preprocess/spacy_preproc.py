"""
spaCy-based preprocessor

Responsibility
--------------
Take the raw article text from a Fetcher and return a cleaned Article:
- normalize whitespace and quotes 
- split into sentences reliably (spaCy sentencizer)
- optionally filter very short/very long sentences
- lightly scrub boilerplate markers commonly seen in by-laws/news articles 

Notes
-----
- This module does not do summarization, it just prepares the text for it. 
- Keep transformations conservative to avoid losing meaning. 
- If a specialized preprocesor is required with heavier rules (ex: section-number, mapping), it can be extended 
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import List, Optional

import spacy

from ..core.models import Article
from ..core.contracts import Preprocessor



# Focused text helpers 

_WS_RE = re.compile(r"[ \t\f\v]+")
_NL_RE = re.compile(r"\n{3,}")
_BULLET_PREFIX_RE = re.compile(
    r"^\s*(?:•|-|–|—|\([a-zA-Z0-9]+\)|[0-9]+(?:\.[0-9]+)*\)|[0-9]+(?:\.[0-9]+)*)\s+"
)

# Examples matched:
#  • item   - item   – item   — item
#  (a) item  (1) item  1. item  1.2.3 item

_LEADING_BYLAW_MARKERS = (
    "whereas",
    "be it enacted",
    "by-law no",
    "bylaw no",
)


def _normalize_whitespace(text: str) -> str:
    """Collapse weird whitespace while preserving paragraphs."""
    text = _WS_RE.sub(" ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _NL_RE.sub("\n\n", text)
    return text.strip()


def _normalize_quotes(text: str) -> str:
    """Normalize curly quotes/dashes to straight ones for simpler downstream logic."""
    return (
        text.replace("“", '"').replace("”", '"')
        .replace("‘", "'").replace("’", "'")
        .replace("–", "-").replace("—", "-")
    )


def _strip_bullet_prefix(sent: str) -> str:
    """Remove common bullet/numbering prefix from a sentence."""
    return _BULLET_PREFIX_RE.sub("", sent).strip()


def _looks_like_bylaw_header(sent: str) -> bool:
    """Detect boilerplate headers found in by-laws"""
    s = sent.strip().lower()
    return any(s.startswith(m) for m in _LEADING_BYLAW_MARKERS)




# spaCy preprocessor 

class SpacyPreprocessor(Preprocessor):
    """
    Clean and normalize article text using spaCy for sentence segmentation.
    
    Parameters
    ----------
    model: str 
        spaCy model name. Default "en_core_web_sm".
    min_sentence_chars : int
        Drop sentences shorter than this (after trimming prefixes). Default 25.
    max_sentence_chars : int | None
        If set, drop sentences longer than this to avoid runaway lines. Default to None.
    drop_bylaw_boilerplate : bool
        If True, drop obvious by-law boilerplate headers ("WHEREAS...", "BY-LAW NO..."). Default to True
    """
    
    def __init__(
        self,
        model: str = "en_core_web_sm",
        *,
        min_sentence_chars: int = 25,
        max_sentence_chars: Optional[int] = None,
        drop_bylaw_boilerplate: bool = True,
    ) -> None:
        
        self.min_sentence_chars = min_sentence_chars
        self.max_sentence_chars = max_sentence_chars
        self.drop_bylaw_boilerplate = drop_bylaw_boilerplate
        
        
        # Load spaCy with only what we need for sentence boundaries 
        self.nlp = spacy.load(
            model,
            disable=["ner", "tagger", "lemmatizer", "attribute_ruler", "parser"],
        )
        # Ensure we have a sentence boundary component 
        if "senter" not in self.nlp.pipe_names and "sentencizer" not in self.nlp.pipe_names:
            self.nlp.add_pipe("sentencizer")
    
    
    def process(self, article: Article) -> Article:
        """
        Return a new Article with cleaned text.
        
        Steps:
        1) normalize whitespace/quotes
        2) run spaCy sentencizer
        3) strip list/bullet prefixes
        4) filter too-short/too-long sentences 
        5) (optional) drop obvious by-law boilerplate headers 
        6) reassemble into a clean paragraph-friendly string
        """
        raw = article.text or ""
        if not raw.strip():
            return article # Nothing to do, return article as-is
        
        
        # Light normalization that helps sentence splitting and ranking 
        norm = _normalize_quotes(_normalize_whitespace(raw))
        
        
        # Sentence segmentation 
        doc = self.nlp(norm)
        sentences: List[str] = []
        for s in doc.sents:
            sent = s.text.strip()
            if not sent:
                continue

            # Remove bullets/numbering list "1.2.3)" or "(a)" or "*"
            sent = _strip_bullet_prefix(sent)
            
            # Optionally drop by-law boilerplate headers 
            if self.drop_bylaw_boilerplate and _looks_like_bylaw_header(sent):
                continue

            # Length filters 
            if len(sent) < self.min_sentence_chars:
                continue
            if self.max_sentence_chars is not None and len(sent) > self.max_sentence_chars:
                continue

            sentences.append(sent)

        # If everything got filtered, fall back to normalized text 
        cleaned_text = " ".join(sentences) if sentences else norm
        
        return replace(article, text=cleaned_text) # Create a new immutable Article instance 
        