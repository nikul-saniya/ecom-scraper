# config.py

BASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

DELAY_RANGE = (2, 5)  # seconds

FILTERS = {
    "min_reviews": 50,
    "min_rating": 4.0,
    "availability": True  # Only in-stock
}
