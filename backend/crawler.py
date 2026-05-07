"""
crawler.py — Cào khách sạn và reviews từ Traveloka
"""

import time
import random
import re
import os
import argparse
import logging
import pandas as pd
import requests
from tqdm import tqdm
import undetected_chromedriver as uc
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup

from database import init_db, upsert_hotel, insert_reviews_batch, save_absa_scores

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ── District URLs ────────────────────────────────────────────────────

DISTRICT_URLS = {
    "hcm": {
        "District 1":  "https://www.traveloka.com/vi-vn/hotel/vietnam/city/district-1-10010551",
        "Bình Thạnh":  "https://www.traveloka.com/vi-vn/hotel/vietnam/city/binh-thanh-district-10010047",
        "District 7":  "https://www.traveloka.com/vi-vn/hotel/vietnam/city/district-7-10009945",
        "District 2":  "https://www.traveloka.com/vi-vn/hotel/vietnam/city/district-2-10010550",
        "Tân Bình":    "https://www.traveloka.com/vi-vn/hotel/vietnam/city/tan-binh-district-10010618",
        "District 4":  "https://www.traveloka.com/vi-vn/hotel/vietnam/city/district-4-10010553",
        "District 3":  "https://www.traveloka.com/vi-vn/hotel/vietnam/city/district-3-10010553",
        "District 10": "https://www.traveloka.com/vi-vn/hotel/vietnam/city/district-10-10010559",
    },
    "hanoi": {
        "Hoàn Kiếm": "https://www.traveloka.com/vi-vn/hotel/vietnam/city/hoan-kiem-district-10010298",
        "Ba Đình":    "https://www.traveloka.com/vi-vn/hotel/vietnam/city/ba-dinh-district-10009977",
        "Đống Đa":    "https://www.traveloka.com/vi-vn/hotel/vietnam/city/dong-da-district-10010227",
        "Tây Hồ":     "https://www.traveloka.com/vi-vn/hotel/vietnam/city/tay-ho-district-10010648",
        "Cầu Giấy":   "https://www.traveloka.com/vi-vn/hotel/vietnam/city/cau-giay-district-10010097",
    },
    "danang": {
        "Hải Châu":      "https://www.traveloka.com/vi-vn/hotel/vietnam/city/hai-chau-district-10010275",
        "Sơn Trà":       "https://www.traveloka.com/vi-vn/hotel/vietnam/city/son-tra-district-10010303",
        "Ngũ Hành Sơn": "https://www.traveloka.com/vi-vn/hotel/vietnam/city/ngu-hanh-son-district-10010491",
        "Thanh Khê":     "https://www.traveloka.com/vi-vn/hotel/vietnam/city/thanh-khe-district-10010082",
    },
}

CITY_NAMES = {
    "hcm":    "Ho Chi Minh City",
    "hanoi":  "Hanoi",
    "danang": "Da Nang",
}

REVIEW_API_URL = "https://www.traveloka.com/api/v2/ugc/review/consumption/v2/getReviews"

COOKIES = os.environ.get("TRAVELOKA_COOKIES", "_fbp=fb.1.1774245104350.426463206249824004; _gcl_au=1.1.1370925220.1774245104; _fwb=33vbA6BeNI52D0HjyYlCKO.1774245104651; _tt_enable_cookie=1; _ttp=01KMCKZK2D1KRPFGCZ9H483FFN_.tt.1; _cs_c=1; __lt__cid=c612afa8-1d22-4bdb-9478-81dafee5c987; _yjsu_yjad=1774245105.7c5e448c-7556-4e91-bbd9-af5751a47250; _kmpid=km|www.traveloka.com|1774245105151|5a8d6250-ad68-47fe-be9f-f7409e4c1d62; _kmpid=km|traveloka.com|1774245105151|5a8d6250-ad68-47fe-be9f-f7409e4c1d62; _ly_su=1774245105.7c5e448c-7556-4e91-bbd9-af5751a47250; __spdt=76abe4c7e6f24467a96b9e51ca16bbf6; _pin_unauth=dWlkPU5EZGxNV1V3WVRBdE16YzJPQzAwWW1RNUxXSXlZbU10TlRZd1lXVXdNREJrTkRWbA; tv-repeat-visit=true; countryCode=VN; tv_cs=1; _gcl_gs=2.1.k1$i1778136454$u55641070; _gid=GA1.2.1819264690.1778136461; _gac_UA-29776811-12=1.1778136461.CjwKCAjwzevPBhBaEiwAplAxvsklW5Ye-gSkHjPtGhsCudN5790-hMMbCM1rcFo7-RifIKLYamr1QBoCWYwQAvD_BwE; _cs_cvars=%7B%226%22%3A%5B%22Referrer%22%2C%22https%3A%2F%2Fwww.google.com%2F%22%5D%7D; tv_user={\"authorizationLevel\":100,\"id\":null}; clientSessionId=T1-web.01KR0NQ8ZPW9H5J3Z6CXBSYZ42; __lt__sid=9c547732-f1c9076a; datadome=zx1JEikVfSFSK~SIASpJ33PtN1Igo1BfSgjrzPet9EOlv~LrApCgjDLOD9eN3qwN5ypssufht5acZ1tNAU6dzy8mR7lnUdrYLmp3MrMCyyL3WSE5atOysseZkmLgmO0D; aws-waf-token=4572bfaa-dab2-4f31-b81d-d1ffbb79ccbc:NQoAeEU7QU4JAAAA:091EGyXGi2R3prJbF5RKskbwyvCHQolaNsJFnpJkwLqoeR3U6o04qIJBFEFg3E8YBRBSVTX+8QU5g17Zo9fHcmVrY50RH8QyLenuRJ0H8tp+YONAqUe95R6Ldy6iH/voXKqbyYRGmSQb/mMUTBKWqjpP9RZuuYpKETWvxEkTsjOFLVR3a6fMuvb6wDG1Zi7dLqU=; tvl=qgdHX7GvehrD9XH5a3S4PUiOJGezXQ9yizVaSxTklwrLYY64AE4apiD1qmHRGaV8gGAQoV6xR5wi1hxtboYegx0JoHbuxL9J5IDMykh7yrkDV+tDU0tOQZDC0wf5Bz7Ih8SGYm0D03zEW7S7g02l9zkAPbkMGQ6AJj+0Bs51j2ei5h9RocdWDc9rnNd7rjzFW0edkpBgwIZ/ZUlGk76ef9AyyLqlGI8HVaqyZv1sD9wee4VU7vQ/UyMBwrs3oM/UF/wlr/KP6nzzFfZhQArkk28V1sV//2lM5WC4+y9QssvM0WMA1zSky7I1/5su3gOqC9i5iQwtBQn4yW2FHNrTumq0cSedozYNf1KNwANoL5+/aEBjLOXk3FzIIcBWDABUxbVWc9mUJC6U6r8wkx04c+4CDTx/jJt5ZXoEQTwGFtmHZU735+1hw0x1oRQl6dDf7veLx2+f12FgAD3Xp2Dyrla7BVWkremvqxTLgQ8GRDmWjxuYwdqXt9lWjLikJxC1H+WzeIeWPbsPfCDu9N+3vnr/5nGuHkxz7gZqA3ZfJnQIWephikxIJEvzI9ABcU8x; tvs=qgdHX7GvehrD9XH5a3S4PXWKx93/3Xi103f/kPpnhg1IQez7AjqOPow88qqCMiL7CqvJjpn5Z2svD8QZzAmUN07gmFQkK2qgsdbWEYgFfB5uk0fUx7sD+NMcK9CmgVocrii3pNJ2kgG/MGUmzAKhwmCIB1NXpx+g05VnrVlNT1r5u09yAru40JsnILlCW/AxKSiBlrZrlAUmMG66Ti79MjAZLJlq2O+W2ii0wMogn1wRSGht0mfSBl6aCgW/bh0Dg43qby0ICwtMQsEEYY/mJ063CCJo+Z+R9n/X0FgUdFdWi6NKpEDgL3xVNnQjLp40FhrkmWFU4Pn0+ElScsbvvevfvLD7R6wzk+E+3UGNVB6sStRtF7qElnLdB0dOiDupsjy7aAp4Ekz/a8/Nool5Oz0Uum36nobT+QnfzO2VKiA148X15DpeseJWr8HNycgbWwzRdqkl2uDNelIJsunwx0/mVRR5m+rCDxlr/mxc7ctk/7BvfeakecrLGNt93lmVM3eEzMiYVzLO8gLbB5/F+g==; sen_t=Adt8GUJ1X7bxooxuwB2guDQzGmfI6WEjCzgBbPwvVQwfEkEFu1TjVIzNdSWuJdlUkwHWGkLDw2Ss0uAGjGtm+1CzVh4tyX8GCSA2/PLlDNXQpR28gm/CzPqc9q0N")

HEADERS = {
    "Content-Type":       "application/json",
    "Accept":             "*/*",
    "User-Agent":         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Cookie":             COOKIES,
    "x-domain":           "ugcReview",
    "x-client-interface": "desktop",
    "x-route-prefix":     "vi-vn",
    "Origin":             "https://www.traveloka.com",
    "Referer":            "https://www.traveloka.com/",
}

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
IDS_CSV  = os.path.join(DATA_DIR, "hotel_ids.csv")


# ── WebDriver ────────────────────────────────────────────────────────

def get_driver() -> uc.Chrome:
    opts = uc.ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=vi-VN")
    driver = uc.Chrome(options=opts, version_main=147)  # chỉ định Chrome 147
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def human_delay(min_s: float = 3, max_s: float = 7):
    time.sleep(random.uniform(min_s, max_s))


def human_scroll(driver, steps: int = 8):
    """Scroll từ từ như người thật."""
    for _ in range(steps):
        amount = random.randint(300, 700)
        driver.execute_script(f"window.scrollBy(0, {amount});")
        time.sleep(random.uniform(0.8, 2.0))


def human_mouse(driver):
    """Di chuyển chuột ngẫu nhiên."""
    try:
        actions = ActionChains(driver)
        for _ in range(3):
            x = random.randint(200, 900)
            y = random.randint(200, 600)
            actions.move_by_offset(x, y)
            time.sleep(random.uniform(0.3, 0.8))
        actions.perform()
    except Exception:
        pass


# ── Bước 1: Cào hotel IDs ───────────────────────────────────────────

def scrape_district(driver, url: str, city_key: str, district_name: str,
                    hotels_per_district: int = 20) -> list:
    city_name  = CITY_NAMES[city_key]
    hotel_data = []

    log.info(f"  Cào quận: {district_name} | {url}")
    driver.get(url)
    human_delay(5, 10)
    human_mouse(driver)

    try:
        WebDriverWait(driver, 25).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/hotel/vietnam/']"))
        )
        log.info("  ✅ Trang đã render xong")
    except Exception:
        log.warning("  ⚠️ Timeout — thử đọc anyway")

    human_scroll(driver, steps=8)

    soup        = BeautifulSoup(driver.page_source, "html.parser")
    all_a       = soup.find_all("a", href=True)
    all_href    = [a.get("href", "") for a in all_a]
    hotel_hrefs = [h for h in all_href if "/hotel/" in h]

    log.info(f"  DEBUG — Tổng links /hotel/: {len(hotel_hrefs)}")
    for h in hotel_hrefs[:5]:
        log.info(f"    {h}")

    # Filter KS thực
    hotel_links = []
    seen_ids    = set()
    for href in hotel_hrefs:
        if re.search(r"/(city|region|area|search)/", href):
            continue
        match = re.search(r"-(\d{7,})(?:\?|$)", href)
        if match and match.group(1) not in seen_ids:
            seen_ids.add(match.group(1))
            hotel_links.append(href)

    log.info(f"  Sau filter: {len(hotel_links)} KS")

    for href in hotel_links[:hotels_per_district]:
        match  = re.search(r"-(\d{7,})(?:\?|$)", href)
        h_id   = match.group(1)
        a_tag  = soup.find("a", href=lambda x: x and href.split("?")[0] in x)
        h3_tag = a_tag.find("h3") if a_tag else None
        h_name = (h3_tag.get_text(strip=True) if h3_tag
                  else href.split("/")[-1].rsplit("-", 1)[0].replace("-", " ").title())

        hotel_data.append({
            "hotel_id":   h_id,
            "hotel_name": h_name,
            "city":       city_name,
            "city_key":   city_key,
            "district":   district_name,
            "url":        f"https://www.traveloka.com{href.split('?')[0]}",
        })

    log.info(f"  → Lấy được {len(hotel_data)} KS")
    return hotel_data


def scrape_hotel_ids(city_key: str = "hcm", district_filter: str = None,
                     hotels_per_district: int = 20) -> pd.DataFrame:
    districts = DISTRICT_URLS.get(city_key, {})
    if not districts:
        log.error(f"Không tìm thấy city_key: {city_key}")
        return pd.DataFrame()

    if district_filter:
        districts = {k: v for k, v in districts.items() if k == district_filter}
        if not districts:
            log.error(f"Không tìm thấy district: {district_filter}")
            return pd.DataFrame()

    all_hotels = []
    driver     = get_driver()

    try:
        # Vào trang chủ trước để có cookies
        driver.get("https://www.traveloka.com/vi-vn")
        human_delay(5, 8)

        for district_name, url in districts.items():
            log.info(f"\n=== Quận: {district_name} ===")
            hotels = scrape_district(driver, url, city_key, district_name, hotels_per_district)
            all_hotels.extend(hotels)
            # Nghỉ lâu giữa các quận
            human_delay(15, 25)
    finally:
        driver.quit()

    df = pd.DataFrame(all_hotels).drop_duplicates(subset=["hotel_id"]) if all_hotels else pd.DataFrame()
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(IDS_CSV) and not df.empty:
        df_old = pd.read_csv(IDS_CSV)
        df     = pd.concat([df_old, df]).drop_duplicates(subset=["hotel_id"])

    if not df.empty:
        df.to_csv(IDS_CSV, index=False, encoding="utf-8-sig")
        log.info(f"\nTổng: {len(df)} hotel IDs → {IDS_CSV}")

    return df


# ── Bước 2: Lấy reviews qua API ─────────────────────────────────────

def crawl_hotel_reviews(hotel_id: str, max_reviews: int = 100) -> list:
    all_reviews = []
    skip        = 0
    limit       = 40

    while len(all_reviews) < max_reviews:
        payload = {
            "fields": [],
            "clientInterface": "desktop",
            "data": {
                "objectId":     str(hotel_id),
                "productType":  "HOTEL",
                "configId":     "REV_CONSV2_HOTEL_GENERAL_V1",
                "filter": {
                    "format":   "FORMAT_VALUE_TEXT",
                    "rating":   "RATING_VALUE_ALL",
                    "language": "LANGUAGE_VALUE_ALL",
                },
                "limit":        str(limit),
                "origin":       "TRAVELOKA",
                "ratingTagSet": [],
                "skip":         str(skip),
                "sort":         "SORT_CREATED_DESCENDING",
            },
        }

        try:
            resp = requests.post(REVIEW_API_URL, json=payload, headers=HEADERS, timeout=20)

            if resp.status_code == 200:
                json_data = resp.json().get("data", {})
                reviews   = json_data.get("reviews", [])
                has_next  = json_data.get("hasNext", False)

                if not reviews:
                    break

                all_reviews.extend(reviews)
                log.info(f"   -> Đã lấy {len(all_reviews)} reviews (skip={skip})")

                if not has_next or len(all_reviews) >= max_reviews:
                    break

                skip += limit
                time.sleep(random.uniform(1.5, 2.5))

            elif resp.status_code == 403:
                log.error("   -> Cookie hết hạn! Cần cập nhật COOKIES mới.")
                break
            else:
                log.warning(f"   -> Lỗi HTTP {resp.status_code}")
                break

        except Exception as e:
            log.error(f"   -> Lỗi: {e}")
            break

    return all_reviews[:max_reviews]


def parse_review(raw: dict) -> dict:
    return {
        "text":            raw.get("reviewContentText", "") or "",
        "reviewer_name":   raw.get("reviewer", {}).get("reviewerName", "Ẩn danh"),
        "review_date":     raw.get("reviewDate", ""),
        "room_facilities": 0,
        "service_staff":   0,
        "location":        0,
        "food_beverage":   0,
        "price_value":     0,
        "general":         0,
    }


# ── Bước 3+4: ABSA + DB ──────────────────────────────────────────────

def analyze_and_save(hotel_row: dict, reviews_raw: list, model_type: str = "phobert"):
    from predictor import predict_batch, compute_absa_summary

    reviews = [parse_review(r) for r in reviews_raw if r.get("reviewContentText")]
    if not reviews:
        log.warning(f"Không có nội dung review cho {hotel_row['hotel_name']}")
        return

    hotel_db = {
        "name":          hotel_row["hotel_name"],
        "url":           hotel_row.get("url", ""),
        "city":          hotel_row["city"],
        "district":      hotel_row.get("district", ""),
        "address":       "",
        "stars":         0,
        "booking_score": 0,
    }
    hotel_id = upsert_hotel(hotel_db)

    log.info(f"Phân tích ABSA {len(reviews)} reviews ({model_type})...")
    texts       = [r["text"] for r in reviews]
    predictions = predict_batch(texts, model_type)

    for review, pred in zip(reviews, predictions):
        review["room_facilities"] = pred["Room_Facilities"]
        review["service_staff"]   = pred["Service_Staff"]
        review["location"]        = pred["Location"]
        review["food_beverage"]   = pred["Food_Beverage"]
        review["price_value"]     = pred["Price_Value"]
        review["general"]         = pred["General"]

    insert_reviews_batch(hotel_id, reviews)
    summary = compute_absa_summary(predictions)
    save_absa_scores(hotel_id, summary)

    log.info(
        f"✅ {hotel_row['hotel_name']} | "
        f"overall={summary.get('overall_score', 0):.1f}% | "
        f"reviews={len(reviews)}"
    )


# ── Pipelines ─────────────────────────────────────────────────────────

def run_ids(city_key: str, district: str = None, hotels_per_district: int = 20):
    scrape_hotel_ids(city_key, district, hotels_per_district)


def run_reviews(max_reviews: int, model_type: str):
    if not os.path.exists(IDS_CSV):
        log.error(f"Không tìm thấy {IDS_CSV}. Chạy --step ids trước!")
        return

    init_db()
    df_ids = pd.read_csv(IDS_CSV)
    log.info(f"Loaded {len(df_ids)} hotel IDs")

    for idx, row in tqdm(df_ids.iterrows(), total=len(df_ids)):
        log.info(f"\n[{idx+1}/{len(df_ids)}] {row['hotel_name']} — {row.get('district','')}")
        reviews_raw = crawl_hotel_reviews(row["hotel_id"], max_reviews)
        analyze_and_save(row.to_dict(), reviews_raw, model_type)
        time.sleep(3)


def run_all(city_key: str, max_reviews: int, model_type: str,
            district: str = None, hotels_per_district: int = 20):
    init_db()
    df_ids = scrape_hotel_ids(city_key, district, hotels_per_district)
    if df_ids.empty:
        log.error("Không lấy được hotel IDs!")
        return

    for idx, row in tqdm(df_ids.iterrows(), total=len(df_ids)):
        log.info(f"\n[{idx+1}/{len(df_ids)}] {row['hotel_name']} — {row.get('district','')}")
        reviews_raw = crawl_hotel_reviews(row["hotel_id"], max_reviews)
        analyze_and_save(row.to_dict(), reviews_raw, model_type)
        time.sleep(3)


# ── Chế độ 2: phân tích URLs tùy chọn ──────────────────────────────

def parse_traveloka_url(url: str):
    from urllib.parse import unquote

    url_decoded = unquote(url)

    # Dang 1: detail page - decode truoc de xu ly %26 trong ten KS
    spec_match = re.search(r"HOTEL\.(\d+)\.(.+?)\.\d+(?:&|$)", url_decoded)
    if spec_match:
        hotel_id   = spec_match.group(1)
        hotel_name = spec_match.group(2).replace("+", " ")
        return hotel_id, hotel_name

    # Dang 2: clean URL slug-{ID}
    slug_match = re.search(r"-(\d{7,})(?:\?|$)", url)
    if slug_match:
        hotel_id   = slug_match.group(1)
        hotel_name = url.split("/")[-1].split("?")[0].rsplit("-", 1)[0].replace("-", " ").title()
        return hotel_id, hotel_name

    return None, None


def analyze_urls(urls: list, max_reviews: int = 50, model_type: str = "phobert") -> list:
    from predictor import predict_batch, compute_absa_summary

    results = []
    for url in urls:
        try:
            hotel_id, hotel_name = parse_traveloka_url(url)
            if not hotel_id:
                results.append({"url": url, "error": "URL không hợp lệ — cần link Traveloka", "scores": {}})
                continue

            log.info(f"Crawling: {hotel_name} (id={hotel_id})")
            reviews_raw = crawl_hotel_reviews(hotel_id, max_reviews)

            if not reviews_raw:
                results.append({"url": url, "name": hotel_name,
                                 "error": "Không cào được reviews — cookie có thể hết hạn", "scores": {}})
                continue

            reviews     = [parse_review(r) for r in reviews_raw if r.get("reviewContentText")]
            predictions = predict_batch([r["text"] for r in reviews], model_type)

            for review, pred in zip(reviews, predictions):
                review["room_facilities"] = pred["Room_Facilities"]
                review["service_staff"]   = pred["Service_Staff"]
                review["location"]        = pred["Location"]
                review["food_beverage"]   = pred["Food_Beverage"]
                review["price_value"]     = pred["Price_Value"]
                review["general"]         = pred["General"]

            summary = compute_absa_summary(predictions)
            results.append({"url": url, "name": hotel_name,
                             "reviews": reviews, "scores": summary, "total": len(reviews)})

        except Exception as e:
            results.append({"url": url, "error": str(e), "scores": {}})

    return results


# ── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HotelSense Crawler — Traveloka")
    parser.add_argument("--step",        choices=["ids", "reviews", "all"], default="all")
    parser.add_argument("--city",        default="hcm",      help="hcm | hanoi | danang")
    parser.add_argument("--district",    default=None,       help="Tên quận, bỏ trống = tất cả")
    parser.add_argument("--hotels",      type=int, default=20)
    parser.add_argument("--max_reviews", type=int, default=100)
    parser.add_argument("--model",       default="logistic", help="phobert | logistic")
    args = parser.parse_args()

    if args.step == "ids":
        run_ids(args.city, args.district, args.hotels)
    elif args.step == "reviews":
        run_reviews(args.max_reviews, args.model)
    else:
        run_all(args.city, args.max_reviews, args.model, args.district, args.hotels)