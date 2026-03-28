import json
from pathlib import Path

import structlog

try:
    from pytrends.request import TrendReq
except ImportError:
    TrendReq = None

logger = structlog.get_logger()

QUERIES = [
    "kids nutrition powder",
    "children supplements India",
    "magnesium gummies kids",
    "protein powder for kids",
    "Nutrimix",
    "Pediasure vs Horlicks",
]


def scrape_trends() -> None:
    output_dir = Path("data/scraped/trends")
    output_dir.mkdir(parents=True, exist_ok=True)

    data: dict[str, dict] = {}

    if TrendReq is None:
        logger.error("pytrends is not installed. Using empty fallback.")
    else:
        try:
            pytrends = TrendReq(hl="en-US", tz=330)
            # pytrends only supports up to 5 terms at once, let's chunk
            pytrends.build_payload(QUERIES[:5], cat=0, timeframe="today 12-m", geo="IN", gprop="")

            iot = pytrends.interest_over_time()
            if not iot.empty:
                iot.index = iot.index.astype(str)
                iot_dict = iot.drop(columns=["isPartial"]).to_dict()
            else:
                iot_dict = {}

            ibr = pytrends.interest_by_region(
                resolution="REGION", inc_low_vol=True, inc_geo_code=False
            )
            ibr_dict = ibr.to_dict() if not ibr.empty else {}

            data = {"interest_over_time": iot_dict, "interest_by_region": ibr_dict}
        except Exception as e:
            logger.error(f"Failed to fetch Google Trends data: {e}")
            logger.warning("Google Trends request failed. Using empty fallback.")

    with open(output_dir / "google_trends.json", "w") as f:
        json.dump(data, f, indent=2)
    logger.info(f"Saved Google Trends data with keys: {list(data.keys())}")


if __name__ == "__main__":
    scrape_trends()
