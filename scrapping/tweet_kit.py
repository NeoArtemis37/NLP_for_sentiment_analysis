#author : artemis37
import asyncio
import pandas as pd
from twikit import Client, TooManyRequests
import logging
import time
import random
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterScraper:
    def __init__(self, username, email, password, locale='en-US'):
        self.client = Client(locale)
        self.username = username
        self.email = email
        self.password = password
        self.tweets_data = []
        
    async def login(self):
        """Try default login, fallback to Method 3 (different user agent) if fails"""
        try:
            await self.client.login(
                auth_info_1=self.username, 
                auth_info_2=self.email, 
                password=self.password
            )
            logger.info("✅ Successfully logged in with default locale")
            return True
        except Exception as e:
            logger.warning(f"Default login failed: {e}")
            # Try Method 3: different user agent / locale
            return await self.login_method_3()
    
    async def login_method_3(self):
        """Method 3: Try login with different locale/user agent"""
        try:
            logger.info("🔑 Trying Method 3 login with 'en-GB' locale")
            self.client = Client('en-GB')  # Change locale here
            await self.client.login(
                auth_info_1=self.username,
                auth_info_2=self.email,
                password=self.password
            )
            logger.info("✅ Method 3 login SUCCESS!")
            return True
        except Exception as e:
            logger.error(f"❌ Method 3 login FAILED: {e}")
            return False
    
    async def scrape_tweets(self, query, max_tweets=5000, delay_range=(2, 5)):
        """Scrape tweets with proper error handling and rate limiting"""
        logger.info(f"Starting to scrape up to {max_tweets} tweets for query: {query}")
        
        try:
            tweets = await self.client.search_tweet(query, product='Latest')
            
            collected_count = 0
            retry_count = 0
            max_retries = 3
            
            while collected_count < max_tweets and retry_count < max_retries:
                try:
                    if tweets and hasattr(tweets, 'items') and tweets.items:
                        for tweet in tweets.items:
                            if collected_count >= max_tweets:
                                break
                            
                            tweet_data = {
                                'id': tweet.id,
                                'text': tweet.text,
                                'created_at': tweet.created_at,
                                'user_screen_name': tweet.user.screen_name,
                                'user_name': tweet.user.name,
                                'retweet_count': tweet.retweet_count,
                                'favorite_count': tweet.favorite_count,
                                'reply_count': getattr(tweet, 'reply_count', 0),
                                'lang': getattr(tweet, 'lang', 'unknown')
                            }
                            
                            self.tweets_data.append(tweet_data)
                            collected_count += 1
                            
                            if collected_count % 50 == 0:
                                logger.info(f"Collected {collected_count} tweets so far...")
                        
                        if collected_count < max_tweets:
                            delay = random.uniform(delay_range[0], delay_range[1])
                            logger.info(f"Waiting {delay:.1f} seconds before next request...")
                            await asyncio.sleep(delay)
                            
                            # Get next page of results
                            if hasattr(tweets, 'next') and callable(tweets.next):
                                tweets = await tweets.next()
                            else:
                                logger.info("No next page available, stopping scraping.")
                                break
                    else:
                        logger.warning("No more tweets found or invalid response")
                        break
                
                except TooManyRequests:
                    retry_count += 1
                    wait_time = (2 ** retry_count) * 60  # exponential backoff
                    logger.warning(f"Rate limit hit. Waiting {wait_time/60:.1f} minutes before retry...")
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    retry_count += 1
                    logger.warning(f"Error during scraping (attempt {retry_count}/{max_retries}): {str(e)}")
                    if retry_count < max_retries:
                        wait_time = (2 ** retry_count) * 60
                        logger.info(f"Waiting {wait_time/60:.1f} minutes before retry...")
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error("Max retries reached, stopping scraper")
                        break
                
        except Exception as e:
            logger.error(f"❌ Critical error during scraping: {str(e)}")
            
        logger.info(f"✅ Scraping completed. Total tweets collected: {len(self.tweets_data)}")
        return self.tweets_data
    
    def save_to_csv(self, filename="twitter_dataset_combined.csv"):
        """Save scraped data to CSV"""
        if self.tweets_data:
            df = pd.DataFrame(self.tweets_data)
            df.to_csv(filename, index=False, encoding='utf-8')
            logger.info(f"✅ Dataset saved: {len(self.tweets_data)} tweets saved to {filename}")
            return df
        else:
            logger.warning("⚠️ No data to save")
            return None

async def main():
    # Configuration
    USERNAME = 'USERNAME'  # Replace with your Twitter username
    EMAIL = 'YOUR_MAIL@INSECURE.NET'  # Replace with your Twitter email
    PASSWORD = 'DROP_YOUR_PASS'  # Replace with your Twitter password
    
    QUERY = '"Université UVBF" OR UVBF OR #UVBF since:2020-01-01 until:2025-09-01'
    MAX_TWEETS = 5000
    
    # Initialize scraper
    scraper = TwitterScraper(USERNAME, EMAIL, PASSWORD)
    
    # Login (tries default, then Method 3)
    if await scraper.login():
        # Scrape tweets
        tweets = await scraper.scrape_tweets(QUERY, MAX_TWEETS)
        
        # Save to CSV
        df = scraper.save_to_csv()
        
        if df is not None:
            print(f"\nScraping Summary:")
            print(f"Total tweets: {len(df)}")
            print(f"Date range: {df['created_at'].min()} to {df['created_at'].max()}")
            print(f"Languages found: {df['lang'].value_counts().to_dict()}")
        
    else:
        logger.error("Failed to login with all methods. Please check your credentials.")

# Run the scraper
if __name__ == "__main__":
    # Set up event loop for Windows compatibility
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
