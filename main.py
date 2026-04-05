import os
import re
import logging
from dotenv import load_dotenv

import google.generativeai as genai
import tweepy
from apify_client import ApifyClient

from prompt import build_prompt_with_tweets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

def fetch_tweets() -> list:
    """Fetches top tweets via Apify Tweet Scraper."""
    logging.info("Fetching tweets from Apify...")
    token = os.environ.get("APIFY_API_TOKEN")
    if not token:
        logging.warning("APIFY_API_TOKEN is missing! Cannot fetch live tweets.")
        return []

    client = ApifyClient(token)
    
    # We will use 'apidojo/tweet-scraper' as it's the most robust free scraper on Apify.
    # Note: Apify uses search parameters. Feel free to adjust searchTerms below.
    run_input = {
        "searchTerms": ["#AI", "ChatGPT", "Sam Altman", "Anthropic", "Claude"],
        "maxItems": 20,
        "sort": "Top",
        "twitterBypass": True
    }

    logging.info("Calling apidojo/tweet-scraper on Apify...")
    run = client.actor("apidojo/tweet-scraper").call(run_input=run_input)
    
    tweets = []
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        if item.get("text"):
            tweets.append({
                "author": item.get("author", {}).get("userName", "Unknown"),
                "likes": item.get("likeCount", 0),
                "reposts": item.get("retweetCount", 0),
                "text": item.get("text", "")
            })
            
    logging.info(f"Fetched {len(tweets)} tweets.")
    return tweets

def analyze_with_ai(tweets: list) -> dict:
    """Passes tweets to Google Gemini API to analyze according to the instructions."""
    logging.info("Analyzing tweets with Google Gemini...")
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is missing!")
        
    genai.configure(api_key=api_key)
    # Using gemini-2.5-flash as it is fast, free to experiment, and highly capable.
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = build_prompt_with_tweets(tweets)
    response = model.generate_content(prompt)
    
    text = response.text
    logging.info(f"AI Response:\n{text}")
    
    # Simple regex parsing to extract fields based on OUTPUT FORMAT
    is_worth_match = re.search(r"Topic Worth Covering:\s*(YES|NO)", text, re.IGNORECASE)
    is_worth = "YES" in is_worth_match.group(1).upper() if is_worth_match else False
    
    summary_match = re.search(r"Summary:\s*(.*?)(?:Reason for Selection:|$)", text, re.IGNORECASE | re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else ""
    
    return {
        "worth_covering": is_worth,
        "summary": summary
    }

def post_to_x(text: str):
    """Posts a tweet or thread to X (Twitter)."""
    logging.info("Publishing to X...")
    
    # Important: The developer portal for X API must be set to 'Read and Write' permission.
    client = tweepy.Client(
        consumer_key=os.environ.get("X_CONSUMER_KEY"),
        consumer_secret=os.environ.get("X_CONSUMER_SECRET"),
        access_token=os.environ.get("X_ACCESS_TOKEN"),
        access_token_secret=os.environ.get("X_ACCESS_TOKEN_SECRET")
    )
    
    # Twitter limits tweets to 280 characters. 
    # Let's chunk the AI summary into a thread if it's longer.
    paragraphs = text.split("\n\n")
    chunks = []
    
    current_chunk = ""
    for p in paragraphs:
        if len(current_chunk) + len(p) + 2 < 275:
            current_chunk += p + "\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            current_chunk = p + "\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    # Post it!
    previous_tweet_id = None
    for i, chunk in enumerate(chunks):
        try:
            # Number threads if multiple e.g., (1/3)
            tweet_text = f"{chunk} ({i+1}/{len(chunks)})" if len(chunks) > 1 else chunk
            
            if not previous_tweet_id:
                response = client.create_tweet(text=tweet_text)
                previous_tweet_id = response.data['id']
            else:
                response = client.create_tweet(text=tweet_text, in_reply_to_tweet_id=previous_tweet_id)
                previous_tweet_id = response.data['id']
                
            logging.info(f"Tweet successfully posted: {response.data['id']}")
            
        except Exception as e:
            logging.error(f"Error posting to X: {e}")
            break

def main():
    # 1. Fetch
    tweets = fetch_tweets()
    if not tweets:
        logging.info("No tweets to process. Exiting.")
        return
        
    # 2. Analyze
    analysis = analyze_with_ai(tweets)
    
    # 3. Post
    if analysis["worth_covering"] and analysis["summary"]:
        logging.info("AI determined topic is worth covering! Posting...")
        # Since it's a dry run setup, we can gate this behind an env var first
        if os.environ.get("DRY_RUN", "true").lower() == "true":
            logging.info(f"[DRY RUN enabled] Would have posted:\n{analysis['summary']}")
        else:
            post_to_x(analysis["summary"])
    else:
        logging.info("AI determined no current topics are worth covering today. Terminating gracefully.")

if __name__ == "__main__":
    main()
