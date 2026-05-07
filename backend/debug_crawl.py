"""
debug_crawl.py — Chay trong thu muc hotelsense_project/backend
    python debug_crawl.py
"""
import sys
sys.path.insert(0, ".")

from crawler import parse_traveloka_url, crawl_hotel_reviews

url = "https://www.traveloka.com/vi-vn/hotel/detail?spec=07-05-2026.08-05-2026.1.1.HOTEL.9000001136359.Cozrum%20Homes%20-%20Coraline%20House.2&loginPromo=1"

print("=== STEP 1: Parse URL ===")
hotel_id, hotel_name = parse_traveloka_url(url)
print(f"hotel_id  = {hotel_id}")
print(f"hotel_name= {hotel_name}")

if not hotel_id:
    print("FAIL: Khong parse duoc URL!")
    sys.exit(1)

print("")
print("=== STEP 2: Crawl reviews ===")
reviews = crawl_hotel_reviews(hotel_id, max_reviews=10)
print(f"So reviews lay duoc: {len(reviews)}")

if reviews:
    print(f"Review dau tien: {reviews[0].get('reviewContentText','')[:100]}")
else:
    print("FAIL: Khong lay duoc reviews!")