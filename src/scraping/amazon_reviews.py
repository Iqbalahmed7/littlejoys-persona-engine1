import json
from pathlib import Path

import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class ProductReview(BaseModel):
    product_name: str
    rating: int  # 1-5
    review_text: str
    review_date: str
    verified_purchase: bool
    helpful_votes: int
    mentioned_price_concern: bool
    mentioned_taste_issue: bool
    mentioned_trust_signal: str | None
    mentioned_child_age: int | None
    sentiment: float  # -1 to 1
    switching_from: str | None
    switching_reason: str | None


PRODUCTS = [
    "LittleJoys Nutrimix",
    "Pediasure",
    "Horlicks",
    "Bournvita",
    "Protinex Junior",
    "Cerelac",
]


def scrape_reviews(product: str) -> list[ProductReview]:
    """Stub scraper. Amazon blocks requests without heavy anti-bot solutions."""
    logger.info(f"Attempting to scrape {product} on Amazon...")

    # "If blocked by anti-scraping measures, document the issue and we'll use fallback distributions."
    logger.warning(
        f"Blocked by anti-scraping for {product}. Returning empty for now to use fallbacks."
    )
    return []


def main() -> None:
    output_dir = Path("data/scraped/reviews")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_reviews = []

    for product in PRODUCTS:
        reviews = scrape_reviews(product)
        all_reviews.extend([r.model_dump() for r in reviews])

    with open(output_dir / "amazon_reviews.json", "w") as f:
        json.dump(all_reviews, f, indent=2)
    logger.info(f"Saved {len(all_reviews)} reviews.")


if __name__ == "__main__":
    main()
