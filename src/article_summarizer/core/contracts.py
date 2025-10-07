"""
Abstract interfaces (contracts) for the summarization pipeline. 

These ABCs keep the system modular and domain-agnostic (by-laws, news, etc).
Implementation (eg. HttpArticleFetcher, SpacyPreprocessor, TextRankSummarizer) 
conform to these interfaces and can be swapped at run time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from .models import Article, Summary

class Fetcher(ABC): # Fetch documents
    """
    Input adapter: obtains a single Article from some source. 
    Ex: HTTP URL fetcher, RSS item fetcher, PDF file fetcher. 
    """
    @abstractmethod
    def fetch(self, input_ref: str) -> Article:
        """
        Retrieve and return an Article from a reference.
        
        Args:
            input_ref: A locator such as:
                - a web URL (ex: "https://example.com/news/")
                - a file path or URI (ex: "/path/to/file.pdf")
                - any custom scheme
        
        Returns:
            Article: populated with text and metadata.
        
        Notes:
            - Fetchers should do retrieval and light parsing only.
            - Heavy cleaning/segmentation is for Preprocessor.
        """
        raise NotImplementedError


class Preprocessor(ABC): # Make the text ready to summarize
    """
    Cleans and normalizes Article text before summarization.
    Ex: strip boilerplate, fix whitespace, sentence segmentation.
    """
    @abstractmethod
    def process(self, article: Article) -> Article:
        """
        Produce a cleaned Article (immutability-friendly: return a new instance).
        
        Args:
            article: the raw or lightly parsed Article from a Fetcher.
        
        Returns:
            Article: Same metadata but with clean text ready for summarizers.
        """
        raise NotImplementedError


class Summarizer(ABC): # Produce the summary
    """
    Core summarization strategy.
    Ex: TextRank (extractive), BART (abstractive).
    """
    
    @abstractmethod
    def summarize(
        self,
        article: Article,
        *,
        max_sentences: int = 5,
        max_tokens: Optional[int] = None,
    ) -> Summary:
        """
        Generate a Summary from a cleaned Article. 
        
        Args:
            article: Preprocessed article text & metadata.
            max_sentences: Soft cap on the number of sentences for extractive methods. 
            max_tokens: Soft cap on generated tokens for abstractive models
        
        Returns:
            Summary: The generated summary object containing final text and provenance
        """
        raise NotImplementedError


class Postprocessor(ABC): # Final touch-ups
    """
    Final polish stage on a Summary.
    Ex: duplicate sentences, length/format normalization, add metadata
    """
    
    @abstractmethod
    def refine(self, summary: Summary) -> Summary:
        """
        Return a refined Summary (immutability-friendly: return a new instance)
        
        Args:
            summary: The raw output from a Summarizer.
        
        Returns:
            Summary: Cleaned version ready for rendering or storage.
        """
        raise NotImplementedError


class Renderer(ABC): # Display the output
    """
    Presents a Summary to an output medium.
    Ex: pretty CLI, JSON string/file, Markdown, PDF.
    """
    
    @abstractmethod
    def render(self, summary: Summary, **fmt_options) -> str | bytes:
        """
        Render the summary and return the rendered payload.
        
        Args:
            summary: The finalized summary to present. 
            **fmt_options: Renderer-specific options (ex: outfile="out.json").
        
        Returns:
            str | bytes: The rendered representation
        """
        raise NotImplementedError