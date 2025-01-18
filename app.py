import os
import sys
import time
import random
from flask import Flask, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words
from functools import wraps
import nltk
import logging
from concurrent.futures import ThreadPoolExecutor

# Download required NLTK data
nltk.download('punkt_tab')
nltk.download('stopwords')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Flask app setup
app = Flask(__name__)

# Rate Limiter Class
class RateLimiter:
    def __init__(self, calls=1, period=1):
        self.calls = calls
        self.period = period
        self.last_reset = time.time()
        self.calls_made = 0

    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()

            if current_time - self.last_reset >= self.period:
                self.calls_made = 0
                self.last_reset = current_time

            if self.calls_made >= self.calls:
                time_to_wait = self.period - (current_time - self.last_reset)
                if time_to_wait > 0:
                    time.sleep(time_to_wait)
                self.calls_made = 0
                self.last_reset = time.time()

            self.calls_made += 1
            return func(*args, **kwargs)
        return wrapper

# Synchronous request function
@RateLimiter(calls=1, period=2)
def make_request(url, headers=None):
    try:
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL {url}: {str(e)}")
        return None

# Summarize article function
def summarize_article(content):
    try:
        max_content_length = 10000
        content = content[:max_content_length] if content else ""

        if not content or len(content.strip()) < 100:
            return "Summary not available."

        parser = PlaintextParser.from_string(content, Tokenizer("english"))
        summarizer = LexRankSummarizer()

        max_sentences = 3
        summary = summarizer(parser.document, max_sentences)

        summary_text = " ".join(str(sentence) for sentence in summary)
        return summary_text if summary_text else "Summary not available."

    except Exception as e:
        print(f"Summarization error: {str(e)}")
        return "Error generating summary."

# Mint Scraper Class
class MintScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.headers = {"User-Agent": self.ua.random}
        self.source_name = "LiveMint"

    def scrape_mint(self):
        try:
            url = "https://www.livemint.com/economy"
            articles = self._scrape_generic(url, "div", "listingNew", "h2", "a", prefix="https://www.livemint.com")
            return articles
        except Exception as e:
            print(f"Error in Mint scraper: {str(e)}")
            return []

    def _scrape_generic(self, url, parent_tag, parent_class, title_tag, link_tag, prefix=""):
        try:
            soup = make_request(url, self.headers)
            if not soup:
                return []

            articles = []
            for item in soup.find_all(parent_tag, class_=parent_class)[:7]:
                try:
                    title_elem = item.find(title_tag)
                    link_elem = item.find(link_tag, href=True)
                    time_elem = item.find("span", {"id": lambda x: x and x.startswith("tListBox_")})

                    if title_elem and link_elem:
                        headline = title_elem.text.strip()
                        link = prefix + link_elem["href"] if prefix else link_elem["href"]
                        time = time_elem.text.strip() if time_elem else "Unknown time"
                        image = self.scrape_image(link)
                        summary = self.summarize_article(link)

                        articles.append({
                            "headline": headline,
                            "link": link,
                            "time": time,
                            "summary": summary,
                            "source": self.source_name,
                            "image": image
                        })
                except Exception as e:
                    print(f"Error processing Mint article: {str(e)}")
                    continue

            return articles
        except Exception as e:
            print(f"Error in Mint generic scraper: {str(e)}")
            return []

    def scrape_image(self, url):
        try:
            soup = make_request(url, self.headers)
            if not soup:
                return None

            figure_tag = soup.find("figure")
            if figure_tag:
                img_tag = figure_tag.find("img")
                if img_tag:
                    return img_tag.get("src")
            return None
        except Exception as e:
            print(f"Error scraping image: {str(e)}")
            return None

    def summarize_article(self, url):
        try:
            soup = make_request(url, self.headers)
            if not soup:
                return {"content": "", "summary": "Summary not available"}

            paragraphs = soup.find_all("p")
            content = " ".join([p.text.strip() for p in paragraphs])
            summary_text = summarize_article(content)

            return {"content": content, "summary": summary_text}
        except Exception as e:
            print(f"Error summarizing article: {str(e)}")
            return {"content": "", "summary": "Error generating summary"}

# Function to run multiple scrapers concurrently and in parallel using ThreadPoolExecutor
def run_scrapers():
    with ThreadPoolExecutor() as executor:
        scrapers = [
            MintScraper().scrape_mint,
            fetch_thehindu_headlines,
            scrape_news18_articles,
            scrape_financial_news
        ]

        results = list(executor.map(lambda scraper: scraper(), scrapers))
    
    return results

# Main route with concurrent scraping using ThreadPoolExecutor
@app.route('/')
def index():
    try:
        # Run scrapers concurrently and in parallel
        results = run_scrapers()

        # Flatten the list of articles from each scraper
        all_articles = []
        for articles in results:
            all_articles.extend(articles)

        # Return results
        if all_articles:
            random.shuffle(all_articles)
            return render_template('index.html', articles=all_articles)
        else:
            return render_template('index.html', articles=[], error="Unable to fetch articles at this time.")
            
    except Exception as e:
        print(f"Error in index route: {str(e)}")
        return render_template('index.html', articles=[], error="An error occurred while fetching articles.")

# Health check endpoint
@app.route('/health')
def health_check():
    return jsonify({"status": "healthy"})

if __name__ == "__main__":
    app.run(debug=True)
