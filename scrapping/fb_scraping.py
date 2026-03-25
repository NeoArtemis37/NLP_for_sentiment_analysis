#!/usr/bin/env python3
"""
Improved Facebook Scraper
WARNING: This script may violate Facebook's Terms of Service.
Use responsibly and consider official APIs for legitimate use cases.
"""
#author : artemis37
import argparse
import time
import json
import csv
import logging
import os
import sys
from typing import List, Dict, Optional
import pandas as pd
from dataclasses import dataclass, asdict
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    StaleElementReferenceException
)
from bs4 import BeautifulSoup
logger = logging.getLogger(__name__)

# Try to import webdriver-manager for automatic ChromeDriver management
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
    logger.info("webdriver-manager is available - ChromeDriver will be managed automatically")
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False
    logger.info("webdriver-manager not available - manual ChromeDriver path may be required")



# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('facebook_scraper.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

@dataclass
class FacebookPost:
    """Data class for Facebook post information"""
    post_id: str = ""
    author: str = ""
    text: str = ""
    link: str = ""
    image_url: str = ""
    timestamp: str = ""
    likes_count: int = 0
    shares_count: int = 0
    comments_count: int = 0
    comments: List[Dict] = None
    
    def __post_init__(self):
        if self.comments is None:
            self.comments = []

class FacebookScraper:
    """Improved Facebook scraper with modern Selenium practices"""
    
    def __init__(self, chromedriver_path: str = "auto", headless: bool = False):
        self.driver = None
        self.wait = None
        if chromedriver_path == "auto":
            self.chromedriver_path = self._find_chromedriver()
        else:
            self.chromedriver_path = chromedriver_path
        self.headless = headless
        self._setup_driver()
    
    def _find_chromedriver(self) -> str:
        """Find chromedriver in common locations or use webdriver-manager"""
        
        # Method 1: Try webdriver-manager (automatic download and management)
        if WEBDRIVER_MANAGER_AVAILABLE:
            try:
                driver_path = ChromeDriverManager().install()
                logger.info(f"ChromeDriver automatically managed at: {driver_path}")
                return driver_path
            except Exception as e:
                logger.warning(f"webdriver-manager failed: {e}, trying manual search")
        
        # Method 2: Search in common system paths
        common_paths = [
            "/usr/local/bin/chromedriver",
            "/usr/bin/chromedriver",
            "/opt/homebrew/bin/chromedriver",  # macOS ARM (M1/M2)
            "/home/linuxbrew/.linuxbrew/bin/chromedriver",  # Linux Homebrew
            "./chromedriver",
            "chromedriver.exe",  # Windows
            "./chromedriver.exe",  # Windows local
        ]
        
        for path in common_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                logger.info(f"Found ChromeDriver at: {path}")
                return path
        
        # Method 3: Try to use ChromeDriver from PATH
        import shutil
        chromedriver_path = shutil.which("chromedriver")
        if chromedriver_path:
            logger.info(f"Found ChromeDriver in PATH: {chromedriver_path}")
            return chromedriver_path
        
        # Method 4: Let Selenium try to find it automatically (newer Selenium versions)
        logger.info("No ChromeDriver found, letting Selenium manage it automatically")
        return None  # This will trigger automatic management in newer Selenium versions
    
    def _setup_driver(self):
        """Setup Chrome driver with optimized options and automatic ChromeDriver management"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
        
        # Performance and stability options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-images")  # Faster loading
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Privacy options
        chrome_options.add_argument("--disable-webrtc")
        chrome_options.add_argument("--disable-webgl")
        
        # Notification settings
        prefs = {
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 2
        }
        chrome_options.add_experimental_option("prefs", prefs)
        
        try:
            # Try different methods to initialize ChromeDriver
            if self.chromedriver_path and self.chromedriver_path != "auto":
                # Method 1: Use specified path
                logger.info(f"Using specified ChromeDriver path: {self.chromedriver_path}")
                service = Service(self.chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            elif self.chromedriver_path:
                # Method 2: Use automatically found path
                logger.info(f"Using automatically found ChromeDriver: {self.chromedriver_path}")
                service = Service(self.chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            else:
                # Method 3: Let Selenium handle it automatically (Selenium 4.6+)
                logger.info("Using Selenium's automatic ChromeDriver management")
                try:
                    self.driver = webdriver.Chrome(options=chrome_options)
                except Exception as selenium_auto_error:
                    logger.warning(f"Selenium auto-management failed: {selenium_auto_error}")
                    
                    # Method 4: Fallback to webdriver-manager if available
                    if WEBDRIVER_MANAGER_AVAILABLE:
                        logger.info("Falling back to webdriver-manager")
                        service = Service(ChromeDriverManager().install())
                        self.driver = webdriver.Chrome(service=service, options=chrome_options)
                    else:
                        raise selenium_auto_error
            
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, 10)
            logger.info("Chrome driver initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            logger.info("Try one of these solutions:")
            logger.info("1. Install webdriver-manager: pip install webdriver-manager")
            logger.info("2. Download ChromeDriver manually and specify path with --chromedriver")
            logger.info("3. Install ChromeDriver in your PATH")
            logger.info("4. Update to Selenium 4.6+ for automatic management")
            raise


    def login(self, email: str, password: str) -> bool:
        """Login to Facebook with improved error handling"""
        try:
            logger.info("Attempting to login to Facebook...")
            self.driver.get("https://www.facebook.com/login")
            
            # Wait for login form
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            password_field = self.driver.find_element(By.ID, "pass")
            login_button = self.driver.find_element(By.NAME, "login")
            
            # Clear and enter credentials
            email_field.clear()
            email_field.send_keys(email)
            password_field.clear()
            password_field.send_keys(password)
            
            # Click login
            login_button.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Check if login was successful
            if "login" in self.driver.current_url.lower():
                logger.error("Login failed - still on login page")
                return False
                
            logger.info("Login successful")
            return True
            
        except TimeoutException:
            logger.error("Timeout during login process")
            return False
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False
    
    def safe_scroll(self, pause_time: float = 2) -> bool:
        """Safely scroll page with duplicate detection"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Scroll to bottom
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(pause_time)
            
            # Check if new content loaded
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            return new_height > last_height
            
        except Exception as e:
            logger.warning(f"Scroll error: {e}")
            return False
    
    def extract_post_data(self, post_element) -> FacebookPost:
        """Extract data from a single post element"""
        post = FacebookPost()
        
        try:
            # Extract post text
            try:
                # Try multiple selectors for post text
                text_selectors = [
                    '[data-ad-preview="message"]',
                    '[data-testid="post_message"]',
                    '.userContent',
                    '.x11i5rnm.xat24cr.x1mh8g0r'
                ]
                
                for selector in text_selectors:
                    try:
                        text_element = post_element.find_element(By.CSS_SELECTOR, selector)
                        post.text = text_element.text.strip()
                        if post.text:
                            break
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                logger.debug(f"Could not extract text: {e}")
            
            # Extract author
            try:
                author_selectors = [
                    'a[role="link"][tabindex="0"]',
                    '.actor-link',
                    '[data-testid="post_chevron_title"]'
                ]
                
                for selector in author_selectors:
                    try:
                        author_element = post_element.find_element(By.CSS_SELECTOR, selector)
                        post.author = author_element.text.strip()
                        if post.author:
                            break
                    except NoSuchElementException:
                        continue
                        
            except Exception as e:
                logger.debug(f"Could not extract author: {e}")
            
            # Extract post URL/ID
            try:
                link_elements = post_element.find_elements(By.CSS_SELECTOR, 'a[href*="/posts/"]')
                if link_elements:
                    post.link = link_elements[0].get_attribute('href')
                    post.post_id = self._extract_post_id_from_url(post.link)
            except Exception as e:
                logger.debug(f"Could not extract post link: {e}")
            
            # Extract image if present
            try:
                img_element = post_element.find_element(By.CSS_SELECTOR, 'img[src*="scontent"]')
                post.image_url = img_element.get_attribute('src')
            except NoSuchElementException:
                pass  # No image in post
            except Exception as e:
                logger.debug(f"Could not extract image: {e}")
            
            # Extract engagement counts
            self.extract_engagement_counts(post_element, post)
            
            # Extract comments (optional)
            self.extract_comments(post_element, post, max_comments=5)
                
        except Exception as e:
            logger.warning(f"Error extracting post data: {e}")
        
        return post
    
    def _extract_post_id_from_url(self, url: str) -> str:
        """Extract post ID from Facebook URL"""
        try:
            if "/posts/" in url:
                return url.split("/posts/")[1].split("?")[0]
            elif "story_fbid=" in url:
                return url.split("story_fbid=")[1].split("&")[0]
        except:
            pass
        return ""
    
    def expand_post_text(self, post_element) -> bool:
        """Try to expand 'See More' links in posts"""
        try:
            see_more_selectors = [
                '[role="button"][tabindex="0"]',
                '.see_more_link',
                'span[dir="auto"]'  # Generic selector for "See More"
            ]
            
            for selector in see_more_selectors:
                try:
                    see_more_buttons = post_element.find_elements(By.CSS_SELECTOR, selector)
                    for button in see_more_buttons:
                        if "voir plus" in button.text.lower() or "see more" in button.text.lower():
                            self.driver.execute_script("arguments[0].click();", button)
                            time.sleep(1)
                            return True
                except:
                    continue
            return False
        except Exception as e:
            logger.debug(f"Could not expand post: {e}")
            return False
    
    def extract_engagement_counts(self, post_element, post: FacebookPost):
        """Extract likes, shares, and comments counts from a post element"""
        try:
            # Likes
            try:
                likes_element = post_element.find_element(By.CSS_SELECTOR, '[aria-label*="like"]')
                likes_text = likes_element.get_attribute('aria-label')
                post.likes_count = self._parse_count_from_text(likes_text)
            except NoSuchElementException:
                post.likes_count = 0

            # Shares
            try:
                shares_element = post_element.find_element(By.XPATH, './/a[contains(@href, "/shares/")]')
                shares_text = shares_element.text
                post.shares_count = self._parse_count_from_text(shares_text)
            except NoSuchElementException:
                post.shares_count = 0

            # Comments
            try:
                comments_element = post_element.find_element(By.XPATH, './/a[contains(@href, "/comments/")]')
                comments_text = comments_element.text
                post.comments_count = self._parse_count_from_text(comments_text)
            except NoSuchElementException:
                post.comments_count = 0

        except Exception as e:
            logger.debug(f"Error extracting engagement counts: {e}")

    def _parse_count_from_text(self, text: str) -> int:
        """Parse integer count from text like '12 likes', '1.2K shares'"""
        try:
            text = text.lower().replace(',', '').strip()
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1_000_000)
            else:
                # Extract digits
                import re
                match = re.search(r'\d+', text)
                if match:
                    return int(match.group())
        except Exception:
            pass
        return 0

    def extract_comments(self, post_element, post: FacebookPost, max_comments: int = 5):
        """Extract top-level comments from a post element"""
        try:
            comment_elements = post_element.find_elements(By.CSS_SELECTOR, '[aria-label="Comment"]')
            for comment_el in comment_elements[:max_comments]:
                try:
                    author = comment_el.find_element(By.CSS_SELECTOR, 'a').text
                    text = comment_el.find_element(By.CSS_SELECTOR, 'span').text
                    post.comments.append({'author': author, 'text': text})
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"Error extracting comments: {e}")
    
    def scrape_search_results(self, search_url: str, max_posts: int = 50, scroll_limit: int = 10) -> List[FacebookPost]:
        """Scrape posts from Facebook search results"""
        posts_data = []
        seen_posts = set()
        scroll_count = 0
        
        try:
            logger.info(f"Navigating to search URL: {search_url}")
            self.driver.get(search_url)
            time.sleep(5)
            
            while len(posts_data) < max_posts and scroll_count < scroll_limit:
                # Find all post elements
                post_selectors = [
                    '[data-ad-preview="message"]',
                    '[data-testid="post_message"]',
                    '.userContentWrapper'
                ]
                
                posts_found = []
                for selector in post_selectors:
                    try:
                        posts_found = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if posts_found:
                            break
                    except:
                        continue
                
                logger.info(f"Found {len(posts_found)} posts on current view")
                
                # Process each post
                for post_element in posts_found:
                    try:
                        # Try to expand post text
                        self.expand_post_text(post_element)
                        
                        # Extract post data
                        post_data = self.extract_post_data(post_element)
                        
                        # Skip if we've seen this post (deduplicate by text + author)
                        post_key = f"{post_data.author}:{post_data.text[:100]}"
                        if post_key in seen_posts:
                            continue
                        
                        seen_posts.add(post_key)
                        
                        # Only add if we have meaningful content
                        if post_data.text.strip() or post_data.author.strip():
                            posts_data.append(post_data)
                            logger.info(f"Extracted post #{len(posts_data)} by {post_data.author}")
                        
                        if len(posts_data) >= max_posts:
                            break
                            
                    except StaleElementReferenceException:
                        logger.debug("Stale element reference, skipping")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing post: {e}")
                        continue
                
                # Scroll down
                if not self.safe_scroll():
                    logger.info("No more content to load")
                    break
                    
                scroll_count += 1
                logger.info(f"Completed scroll {scroll_count}/{scroll_limit}")
                
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
        
        logger.info(f"Scraping completed. Extracted {len(posts_data)} unique posts")
        return posts_data
    
    def scrape_page_posts(self, page_url: str, max_posts: int = 50) -> List[FacebookPost]:
        """Scrape posts from a specific Facebook page"""
        return self.scrape_search_results(page_url, max_posts)
    
    def save_data(self, posts: List[FacebookPost], output_format: str = "csv", filename: str = "facebook_posts"):
        """Save scraped data in various formats"""
        if not posts:
            logger.warning("No data to save")
            return
        
        # Convert to dictionary format
        data_dicts = [asdict(post) for post in posts]
        
        if output_format.lower() == "csv":
            df = pd.DataFrame(data_dicts)
            csv_file = f"{filename}.csv"
            df.to_csv(csv_file, index=False, encoding='utf-8')
            logger.info(f"Data saved to {csv_file}")
            
        elif output_format.lower() == "json":
            json_file = f"{filename}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data_dicts, f, ensure_ascii=False, indent=2)
            logger.info(f"Data saved to {json_file}")
            
        elif output_format.lower() == "txt":
            txt_file = f"{filename}.txt"
            with open(txt_file, 'w', encoding='utf-8') as f:
                for i, post in enumerate(posts, 1):
                    f.write(f"=== POST {i} ===\n")
                    f.write(f"Author: {post.author}\n")
                    f.write(f"Text: {post.text}\n")
                    f.write(f"Link: {post.link}\n")
                    f.write(f"Likes: {post.likes_count}\n")
                    f.write(f"Shares: {post.shares_count}\n")
                    f.write(f"Comments Count: {post.comments_count}\n")
                    f.write(f"Comments:\n")
                    for comment in post.comments:
                        f.write(f"  - {comment['author']}: {comment['text']}\n")
                    f.write("-" * 50 + "\n")
            logger.info(f"Data saved to {txt_file}")

    def close(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed")

def get_credentials(scraper, credentials_list: List[tuple]) -> tuple:
    """
    Try multiple credentials until login succeeds.
    Returns (email, passsword) of successful login or (None, None).
    """
    for email, password in credentials_list:
        logger.info(f"Trying login with {email}")
        if scraper.login(email, password):
            logger.info(f"Login successful with {email}")
            return email, password
        else:
            logger.warning(f"Login failed with {email}")
    logger.error("All login attempts failed.")
    return None, None

def load_credentials_from_file(filepath: str) -> List[tuple]:
        creds = []
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    email, password = line.split(':', 1)
                    creds.append((email.strip(), password.strip()))
        except Exception as e:
            logger.error(f"Failed to read credentials file: {e}")
        return creds
def main():
    """Main function with CLI interface"""
    parser = argparse.ArgumentParser(description="Improved Facebook Scraper")
    parser.add_argument('-u', '--url', required=True, 
                        help='Facebook URL to scrape (page or search results)')
    parser.add_argument('-n', '--num-posts', type=int, default=50,
                        help='Maximum number of posts to scrape (default: 50)')
    parser.add_argument('-o', '--output', choices=['csv', 'json', 'txt'], default='csv',
                        help='Output format (default: csv)')
    parser.add_argument('-f', '--filename', default='facebook_posts',
                        help='Output filename without extension (default: facebook_posts)')
    parser.add_argument('--headless', action='store_true',
                        help='Run browser in headless mode')
    parser.add_argument('--chromedriver', 
                        help='Path to chromedriver executable')
    parser.add_argument('--credentials_file', default='credentials.txt',
                    help='Path to credentials file (default: credentials.txt)')

    
    args = parser.parse_args()
    
    scraper = FacebookScraper(
        chromedriver_path=args.chromedriver if args.chromedriver else "auto",
        headless=args.headless
    )

    credentials_list = load_credentials_from_file(args.credentials_file)
    if not credentials_list:
        logger.error("No credentials loaded. Please check your credentials file.")
        return

    try:
        email, password = get_credentials(scraper, credentials_list)
        if not email or not password:
            logger.error("Could not login with any provided credentials.")
            return

        posts = scraper.scrape_search_results(args.url, args.num_posts)
        scraper.save_data(posts, args.output, args.filename)
        logger.info(f"Successfully scraped {len(posts)} posts")

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
