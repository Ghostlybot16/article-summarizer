"""
Tests for HttpArticleFetcher.

These tests verify that:
- The fetcher successfully retrieves and parses article data from real web URLs.
- The returned object is an Article instance with expected attributes. 

Live HTTP requests are used for integration-style validation.
"""

import pytest 
from article_summarizer.fetchers.http_fetcher import HttpArticleFetcher
from article_summarizer.core.models import Article

@pytest.mark.integration
def test_fetch_valid_article():
    """Fetches a known URL and verifies extracted fields are non-empty."""
    fetcher = HttpArticleFetcher(min_chars=200)
    url = "https://www.bbc.com/news/articles/cj6xje2778go" # Oct 7, 2025 BBC Article regarding USA and Canada
    
    article = fetcher.fetch(url)
    
    # Basic type and field validation 
    assert isinstance(article, Article)
    assert article.url == url
    assert isinstance(article.text, str) and len(article.text) > 200
    assert article.id and isinstance(article.id, str)
    assert article.title is None or isinstance(article.title, str)
    assert isinstance(article.authors, tuple)
    assert article.lang in (None, "en")


def test_reject_non_http_url():
    """Fetcher should raise an error for unsupported protocols."""
    fetcher = HttpArticleFetcher()
    with pytest.raises(RuntimeError):
        fetcher.fetch("file://some/local/path.txt")


def test_reject_short_text(monkeypatch):
    """Ensure very short extracted content raises a RuntimeError"""
    
    def fake_fetch_url(url, timeout=None, user_agent=None):
        return "<html><body>Hi</body></html>"
    
    def fake_extract(*args, **kwargs):
        return "short text"
    
    monkeypatch.setattr("trafilatura.fetch_url", fake_fetch_url)
    monkeypatch.setattr("trafilatura.extract", fake_extract)
    
    fetcher = HttpArticleFetcher(min_chars=100)
    with pytest.raises(RuntimeError):
        fetcher.fetch("https://example.com/article")
    