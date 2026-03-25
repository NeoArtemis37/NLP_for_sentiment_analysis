#author artemis37
import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager as CM
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from dateutil.parser import parse

# --- Login function ---
def login_twitter(driver, username_str, password_str):
    driver.get("https://x.com/i/flow/login")
    try:
        username = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[autocomplete="username"]'))
        )
        username.send_keys(username_str)
        username.send_keys(Keys.RETURN)

        password = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[name="password"]'))
        )
        password.send_keys(password_str)
        password.send_keys(Keys.RETURN)

        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
        )
        print("Login successful.")
        return True
    except TimeoutException:
        print("Login failed or took too long.")
        return False

# --- Helper to get engagement counts ---
def get_engagement(tweet, label):
    try:
        el = tweet.find_element(By.XPATH, f'.//div[@data-testid="{label}"]')
        count = el.text
        return count if count else "0"
    except NoSuchElementException:
        return "0"

# --- Scroll and collect tweets ---
def scroll_and_collect_tweets(driver, max_scrolls=50, scroll_pause=5, output_file="tweets_UVBF.csv"):
    tweets_collected = set()
    tweets_data = []
    scroll_count = 0
    last_height = driver.execute_script("return document.body.scrollHeight")

    while scroll_count < max_scrolls:
        tweets = driver.find_elements(By.CSS_SELECTOR, 'article[data-testid="tweet"]')

        for tweet in tweets:
            try:
                profile_link = tweet.find_element(By.CSS_SELECTOR, 'a[href*="/"]')
                author = profile_link.get_attribute("href").split("/")[-1]
            except NoSuchElementException:
                author = ""

            try:
                tweet_text = tweet.find_element(By.CSS_SELECTOR, 'div[lang]').text
            except NoSuchElementException:
                tweet_text = ""

            try:
                timestamp = tweet.find_element(By.TAG_NAME, "time").get_attribute("datetime")
                tweet_date = parse(timestamp).date().isoformat()
            except Exception:
                tweet_date = ""

            try:
                anchor = tweet.find_element(By.CSS_SELECTOR, "a[aria-label][dir]")
                external_link = anchor.get_attribute("href")
            except Exception:
                external_link = ""

            try:
                images = tweet.find_elements(By.CSS_SELECTOR, 'div[data-testid="tweetPhoto"] img')
                tweet_images = [img.get_attribute("src") for img in images]
            except Exception:
                tweet_images = []

            images_links = ', '.join(tweet_images) if tweet_images else "No Images"

            retweets = get_engagement(tweet, "retweet")
            replies = get_engagement(tweet, "reply")
            likes = get_engagement(tweet, "like")

            tweet_tuple = (author, tweet_text, tweet_date, external_link, images_links, retweets, replies, likes)
            if tweet_tuple not in tweets_collected:
                tweets_collected.add(tweet_tuple)
                tweets_data.append(tweet_tuple)
                print(f"Author: {author}, Date: {tweet_date}, Tweet: {tweet_text[:50]}...")

        # Scroll to bottom with randomized delay
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause + random.uniform(1, 3))

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            print("Reached bottom or no new tweets loaded.")
            break
        last_height = new_height
        scroll_count += 1

        # Save incrementally every 10 scrolls
        if scroll_count % 10 == 0:
            print(f"Saving data after {scroll_count} scrolls...")
            save_to_csv(tweets_data, output_file)

    # Final save
    save_to_csv(tweets_data, output_file)
    return tweets_data

# --- Save to CSV ---
def save_to_csv(data, filename):
    df = pd.DataFrame(data, columns=["Author", "Tweet", "Date", "Link", "Images", "Retweets", "Replies", "Likes"])
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"Saved {len(data)} tweets to {filename}")

# --- Main function ---
def main():
    username_str = "Username"  # Replace with your Twitter username
    password_str = "Pasword"  # Replace with your Twitter password

    # Search query for multiple keywords/hashtags (URL encoded)
    search_query = '%28%22CITADEL%20UVBF%22%20OR%20%22Citadel%20UVBF%22%20OR%20%22Citadelle%20UVBF%22%20OR%20citadel_uvbf%20OR%20%23citadel_uvbf%29'
    search_url = f"https://x.com/search?q={search_query}&f=live"

    options = Options()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--headless")  # Comment this out if you want to see the browser

    service = Service(executable_path=CM().install())
    driver = webdriver.Chrome(service=service, options=options)

    output_file = "tweets_UVBF_final.csv"

    try:
        if not login_twitter(driver, username_str, password_str):
            driver.quit()
            return

        driver.get(search_url)
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'article[data-testid="tweet"]'))
        )

        tweets_data = scroll_and_collect_tweets(driver, max_scrolls=100, scroll_pause=5, output_file=output_file)

        print(f"Total tweets collected: {len(tweets_data)}")
        print(f"Final data saved to {output_file}")

    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
