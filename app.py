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

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

# Increase recursion limit
sys.setrecursionlimit(5000)

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

# Modified request function with rate limiting
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

# Modified summarization function
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
                        summary = self.summarize_article(link)['summary']

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

# Import other scraper functions from their respective files
from hindu2 import fetch_thehindu_headlines
from news18_scraper import scrape_news18_articles
from financial_scraper import scrape_financial_news

# Error handling decorator
def handle_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Error in {func.__name__}: {str(e)}")
            return []
    return wrapper

# Main route with error handling
@app.route('/')
def index():
    try:
        # Initialize empty lists for articles
        all_articles = []
        
        # Add error handling for each scraper
        scrapers = [
            (MintScraper().scrape_mint, "Mint"),
            (fetch_thehindu_headlines, "The Hindu"),
            (scrape_news18_articles, "News18"),
            (scrape_financial_news, "Financial Express")
        ]
        
        for scraper_func, source_name in scrapers:
            try:
                articles = scraper_func()
                if articles:
                    all_articles.extend(articles)
                time.sleep(1)  # Add delay between scrapers
            except Exception as e:
                print(f"Error scraping {source_name}: {str(e)}")
                continue

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
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
