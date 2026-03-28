# PRD-002: Data Enrichment Pipeline

> **Sprint**: 1
> **Priority**: P1 (Important, not blocking)
> **Assignee**: Antigravity
> **Depends On**: PRD-000
> **Status**: Ready for Development
> **Estimated Effort**: 1 day

---

## Objective

Scrape real-world data from sources Indian parents frequent to ground our persona distributions in reality rather than assumptions. Refine the distribution tables from PRD-001 with empirical data.

---

## Deliverables

### D1: Amazon/Flipkart Review Scraper

**File**: `src/scraping/amazon_reviews.py`

Scrape reviews for these products (kids nutrition category):
- LittleJoys Nutrimix
- Pediasure
- Horlicks
- Bournvita
- Protinex Junior
- Cerelac (for younger age reference)

**Extract per review**:
```python
class ProductReview(BaseModel):
    product_name: str
    rating: int                    # 1-5
    review_text: str
    review_date: str
    verified_purchase: bool
    helpful_votes: int
    # Derived (via LLM extraction from review text):
    mentioned_price_concern: bool
    mentioned_taste_issue: bool
    mentioned_trust_signal: str | None  # "doctor recommended", "saw on instagram", etc.
    mentioned_child_age: int | None
    sentiment: float               # -1 to 1
    switching_from: str | None     # Previous product if mentioned
    switching_reason: str | None
```

**Target**: 200+ reviews per product (1200+ total).

### D2: Parenting Forum Scraper

**File**: `src/scraping/parenting_forums.py`

Scrape discussion threads from BabyChakra and ParentCircle related to:
- Child nutrition supplements
- Kids vitamins/gummies
- Protein for kids
- Magnesium for kids
- Health food brands for children

**Extract per thread**:
```python
class ForumThread(BaseModel):
    source: str                    # "babychakra" | "parentcircle"
    title: str
    text: str
    reply_count: int
    # Derived:
    concerns_mentioned: list[str]  # nutrition, immunity, growth, focus, etc.
    brands_mentioned: list[str]
    trust_sources_referenced: list[str]  # doctor, friend, google, influencer
    child_age_range: tuple[int, int] | None
    sentiment_toward_supplements: float  # -1 to 1
```

**Target**: 500+ threads.

### D3: Google Trends Data

**File**: `src/scraping/google_trends.py`

Pull Google Trends data (via pytrends) for:
- "kids nutrition powder"
- "children supplements India"
- "magnesium gummies kids"
- "protein powder for kids"
- "Nutrimix"
- "Pediasure vs Horlicks"

**Extract**:
- Interest over time (last 12 months)
- Interest by region (Indian states)
- Related queries (rising and top)

### D4: Distribution Fitting

**File**: `src/scraping/distribution_fitter.py` (new file)

Take the scraped data and refine distribution parameters:

```python
class DistributionFitter:
    """
    Analyzes scraped data to refine persona attribute distributions.

    Example: If 70% of Amazon reviews mention price concern for products > ₹500,
    the price_sensitivity distribution should have mean > 0.5.
    """

    def fit_from_reviews(self, reviews: list[ProductReview]) -> dict[str, DistributionParams]:
        """Derive distribution parameters from review analysis."""
        ...

    def fit_from_forums(self, threads: list[ForumThread]) -> dict[str, DistributionParams]:
        """Derive distribution parameters from forum analysis."""
        ...

    def fit_from_trends(self, trends_data: TrendsData) -> dict[str, DistributionParams]:
        """Derive awareness_level distributions from search trends."""
        ...

    def merge_with_defaults(
        self, fitted: dict, defaults: dict
    ) -> dict[str, DistributionParams]:
        """Merge fitted distributions with defaults, preferring fitted where available."""
        ...
```

---

## Acceptance Criteria

- [ ] At least 500 reviews scraped and stored in `data/scraped/reviews/`
- [ ] At least 200 forum threads scraped and stored in `data/scraped/forums/`
- [ ] Google Trends data for all 6 queries stored in `data/scraped/trends/`
- [ ] Distribution fitter produces updated parameters stored in `data/distributions/`
- [ ] Scraping is respectful (rate-limited, user-agent set, robots.txt checked)
- [ ] All scraped data is JSON, not raw HTML
- [ ] Fallback distributions exist if scraping is blocked

---

## Risk Mitigation

If scraping is blocked (likely for Amazon):
1. Use a smaller sample from accessible sources
2. Fall back to default distributions in ARCHITECTURE.md §5.3 (these are already reasonable)
3. Supplement with publicly available market research numbers (Redseer reports, Inc42 D2C data)

This PRD is P1, not P0 — the system works with default distributions. Scraped data improves realism but isn't blocking.

---

## Reference Documents

- ARCHITECTURE.md §4.2 (Data Sources for Taxonomy Grounding)
