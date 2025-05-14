import os
import time
import pickle
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
from rapidfuzz import fuzz
import re

# Configuration
COOKIE_FILE = "goodreads_cookies.pkl"
REVIEW_LIMIT_PER_BOOK = 100
CSV_OUTPUT = "reviews_output.csv"
FUZZY_MATCH_THRESHOLD = 75

# Load CSV
input_path = "/Users/oliviapivovar/Desktop/Goodreads Task/goodreads_list.csv"
df = pd.read_csv(input_path)
df['Book ID'] = df['Book ID'].astype(int)
print(df.head())

# Load existing reviews if file exists
if os.path.exists(CSV_OUTPUT):
    existing_df = pd.read_csv(CSV_OUTPUT)
    existing_df['book_id'] = existing_df['book_id'].astype(int)
    valid_book_ids = set(df['Book ID'])
    existing_df = existing_df[existing_df['book_id'].isin(valid_book_ids)]
    all_reviews = existing_df.to_dict(orient="records")
else:
    all_reviews = []
    existing_df = pd.DataFrame()

def create_driver():
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    return webdriver.Chrome(options=options)

def login(driver):
    if os.path.exists(COOKIE_FILE):
        print("\U0001F501 Loading saved cookies...")
        driver.get("https://www.goodreads.com/")
        cookies = pickle.load(open(COOKIE_FILE, "rb"))
        for cookie in cookies:
            driver.add_cookie(cookie)
    else:
        print("\U0001F512 No saved login. Please log in manually...")
        driver.get("https://www.goodreads.com/user/sign_in")
        time.sleep(60)
        pickle.dump(driver.get_cookies(), open(COOKIE_FILE, "wb"))
        print("✅ Cookies saved.")

# Set up Selenium
driver = create_driver()
login(driver)

for index, row in df.iterrows():
    title = row['Title']
    author = row['Author']
    book_id = int(row['Book ID'])

    title = re.sub(r"\[.*?\]|\(.*?\)", "", title).strip()

    existing_reviews = existing_df[existing_df['book_id'] == book_id] if not existing_df.empty else pd.DataFrame()
    existing_count = len(existing_reviews)
    if existing_count >= REVIEW_LIMIT_PER_BOOK:
        print(f"⏭️  Already have {existing_count} reviews for: {title}, skipping...")
        continue
    else:
        remaining_needed = REVIEW_LIMIT_PER_BOOK - existing_count
        print(f"📌 Already have {existing_count} reviews for: {title}, scraping {remaining_needed} more...")

    try:
        query = title
        search_url = f"https://www.goodreads.com/search?q={quote_plus(query)}"
        print(f"\n🔎 Searching: {title} by {author}")

        driver.get(search_url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        book_links = soup.find_all("a", class_="bookTitle")

        best_match = None
        best_score = 0
        undesired_keywords = ["summary", "study-guide", "workbook", "analysis", "notes", "review", "discussion"]

        for idx, result in enumerate(book_links):
            href = result.get("href", "")
            full_text = result.get_text(strip=True).lower()
            if any(word in href.lower() for word in undesired_keywords):
                continue

            title_score = fuzz.partial_ratio(title.lower(), full_text)
            combined_score = fuzz.partial_ratio(f"{title.lower()} {author.lower()}", full_text)

            if title_score >= 90:
                combined_score += 10

            if idx == 0:
                combined_score += 5

            if combined_score > best_score and combined_score >= FUZZY_MATCH_THRESHOLD:
                best_score = combined_score
                best_match = f"https://www.goodreads.com{href}"

        if not best_match:
            print("❌ No suitable book link found.")
            continue

        book_url = best_match
        print("📚 Book page:", book_url)
        driver.get(book_url)

        try:
            more_reviews_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[span[contains(text(), "More reviews and ratings")]]'))
            )
            driver.execute_script("arguments[0].click();", more_reviews_link)
            time.sleep(3)
            print("📄 Navigated to reviews.")
        except Exception as e:
            print("⚠️ Couldn't find 'More reviews':", str(e))
            continue

        reviews_scraped = 0
        page_num = 1

        while reviews_scraped < remaining_needed:
            print(f"\n📄 Scraping page {page_num} ({reviews_scraped} new reviews)...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight / 2);")
            time.sleep(2)

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "ReviewCard")))
            except:
                print("⚠️ ReviewCard not loaded.")
                break

            soup = BeautifulSoup(driver.page_source, "html.parser")
            review_cards = soup.find_all("article", class_="ReviewCard")

            for card in review_cards:
                if reviews_scraped >= remaining_needed:
                    break

                reviewer_id_raw = card.get("aria-label", "")
                if not reviewer_id_raw or "Review by" not in reviewer_id_raw:
                    continue
                reviewer_id = reviewer_id_raw.replace("Review by ", "").strip()

                if not reviewer_id or (not existing_reviews.empty and reviewer_id in existing_reviews['reviewer_ID'].values):
                    continue

                rating_tag = card.find("span", attrs={"aria-label": lambda s: s and "out of 5" in s})
                review_rating = rating_tag["aria-label"].split(" ")[1] if rating_tag else "N/A"
                date_tag = card.find("a", href=lambda h: h and "/review/show" in h)
                review_date = date_tag.get_text(strip=True) if date_tag else "N/A"
                review_text_tag = card.select_one("div.TruncatedContent__text")
                review_text = review_text_tag.get_text(separator="\n", strip=True) if review_text_tag else "N/A"

                likes_tag = card.find("span", string=lambda s: s and "like" in s.lower())
                review_upvotes = likes_tag.get_text(strip=True).split()[0] if likes_tag else "0"

                comments_tag = card.find("span", string=lambda s: s and "comment" in s.lower())
                review_comments = comments_tag.get_text(strip=True).split()[0] if comments_tag else "0"

                shelf_section = card.find("section", class_="ReviewCard__tags")
                shelf_links = shelf_section.find_all("a") if shelf_section else []
                shelf_tags = [a.get_text(strip=True) for a in shelf_links]

                all_reviews.append({
                    "book_id": book_id,
                    "title": title,
                    "author": author,
                    "reviewer_ID": reviewer_id,
                    "review_rating": review_rating,
                    "review_date": review_date,
                    "review_text": review_text,
                    "review_upvotes": review_upvotes,
                    "review_comments": review_comments,
                    "review_shelf_tags": ", ".join(shelf_tags)
                })

                reviews_scraped += 1

            try:
                show_more_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'span[data-testid="loadMore"]'))
                )
                driver.execute_script("arguments[0].click();", show_more_btn.find_element(By.XPATH, './ancestor::button'))
                print("🔁 Clicked 'Show more reviews'")
                page_num += 1
            except:
                print("✅ All reviews loaded or no more pages.")
                break

        print(f"✅ Done scraping {reviews_scraped} reviews for: {title}")
        print(f"📊 Final count for {title}: {existing_count + reviews_scraped} reviews")

        temp_df = pd.DataFrame(all_reviews)
        temp_df['book_id'] = temp_df['book_id'].astype(int)
        temp_df.sort_values(by=['book_id', 'review_date'], inplace=True)
        temp_df.to_csv(CSV_OUTPUT, index=False)
        print(f"💾 Progress saved with {len(temp_df)} reviews so far.\n")

        time.sleep(1.5)

    except Exception as e:
        print(f"❌ Error on book '{title}':", str(e))
        driver.quit()
        driver = create_driver()
        login(driver)
        continue

# FINAL SAVE AND EXIT
driver.quit()
print(f"\n✅ Scraping session complete. All progress saved to {CSV_OUTPUT}")
