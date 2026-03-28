"""
Amazon/Flipkart product review scraper for kids nutrition products.

Full implementation in PRD-002 (Antigravity).
"""

from __future__ import annotations

from pydantic import BaseModel


class ProductReview(BaseModel):
    """Structured review extracted from e-commerce platforms."""

    product_name: str
    rating: int
    review_text: str
    review_date: str
    verified_purchase: bool
    helpful_votes: int
    mentioned_price_concern: bool = False
    mentioned_taste_issue: bool = False
    mentioned_trust_signal: str | None = None
    mentioned_child_age: int | None = None
    sentiment: float = 0.0
    switching_from: str | None = None
    switching_reason: str | None = None


async def scrape_product_reviews(product_name: str, max_reviews: int = 200) -> list[ProductReview]:
    """Scrape reviews for a product from Amazon/Flipkart."""
    raise NotImplementedError("Full implementation in PRD-002")
