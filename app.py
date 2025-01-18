import os
import nltk
from flask import Flask, render_template, jsonify, render_template_string
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from threading import Thread
from dotenv import load_dotenv

load_dotenv()

# Update the app.run() at the bottom
if _name_ == "_main_":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)


app = Flask(__name__)

# Helper function to make requests and parse HTML
def make_request(url, headers=None):
    try:
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=10)  # Timeout after 10 seconds
        response.raise_for_status()  # Raise an error for invalid responses
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL {url}: {str(e)}")
        return None

# News18 Scraper Functions
def scrape_article_content(article_url):
    response = requests.get(article_url, timeout=10)  # Timeout after 10 seconds
    soup = BeautifulSoup(response.content, "html.parser")
    
    article_content = soup.find("article")
    time = soup.find("time")
    article_time = time.text.strip() if time else "Unknown"
    
    image_tag = article_content.find("figure").find("img") if article_content else None
    article_image = image_tag["src"] if image_tag else None
    
    if article_content:
        paragraphs = article_content.find_all("p")
        article_text = "\n".join([para.text.strip() for para in paragraphs])
        return article_text, article_time, article_image
    else:
        print(f"Article content not found for URL: {article_url}")
        return None, None, None

def scrape_news18_articles():
    url = "https://www.news18.com/business/economy/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    blog_list = soup.find_all("div", class_="jsx-50600299959a4159 blog_list_row")
    articles = []

    for blog in blog_list[:8]:  # Limit to 8 articles
        headline = blog.find("h3", class_="jsx-50600299959a4159").text.strip()
        link = blog.find("a", class_="jsx-50600299959a4159")["href"]

        article_content, article_time, article_image = scrape_article_content(link)

        if article_content:
            summary = article_content[:500]  # Simple summary (first 500 characters)
            articles.append({
                "headline": headline,
                "link": link,
                "time": article_time,
                "summary": summary,
                "source": "News18",
                "image": article_image
            })

    return articles

# The Hindu Scraper Functions
def fetch_article_details(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Ensure we get a valid response

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract article content (all paragraph tags)
        paragraphs = soup.find_all('p')
        article_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        # Extract publication time (if available)
        time_tag = soup.find('div', class_='bl-by-line')
        time = None

        if time_tag:
            time_text = time_tag.get_text(strip=True)
            time = time_text.split('|')[0].strip()  # Get the part before the location

        if not time:
            time = "No time available"

        return article_content, time

    except Exception as e:
        print(f"Error fetching article details: {str(e)}")
        return None, "No time available"

def fetch_image_from_article(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Ensure we get a valid response

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find the div with class "picture-big ratio ratio-16x9" for the image
        image_div = soup.find('div', class_='picture-big ratio ratio-16x9')
        image_url = None

        if image_div:
            source_tags = image_div.find_all('source')
            if source_tags:
                largest_image_url = source_tags[-1].get('srcset')

                if largest_image_url and not largest_image_url.startswith('http'):
                    largest_image_url = 'https://bl-i.thgim.com' + largest_image_url
                
                image_url = largest_image_url

        return image_url

    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return None

def fetch_thehindu_headlines():
    url = "https://www.thehindubusinessline.com/economy/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    headlines_list = soup.find("ul", class_="section-result-list")
    articles = []

    if headlines_list:
        for item in headlines_list.find_all("li", itemprop="itemListElement"):
            headline_tag = item.find("h3", class_="title")
            link_tag = item.find("a", itemprop="url")
            if headline_tag and link_tag:
                headline = headline_tag.get_text(strip=True)
                link = link_tag['href']
                if not link.startswith("http"):
                    link = "https://www.thehindubusinessline.com" + link
                
                article_content, time = fetch_article_details(link)
                if article_content:
                    image_url = fetch_image_from_article(link)

                    articles.append({
                        "headline": headline,
                        "link": link,
                        "summary": article_content[:500],  # Just use first 500 characters as summary
                        "time": time,
                        "image": image_url,
                        "source": "The Hindu Business Line"
                    })

    return articles

# Flask Route to serve all scraped data
@app.route('/')
def index():
    # Fetch articles from News18
    news18_articles = scrape_news18_articles()

    # Fetch articles from The Hindu
    hindu_articles = fetch_thehindu_headlines()

    # Combine all articles
    all_articles = news18_articles + hindu_articles

    # Render the HTML template and pass the articles to it
    return render_template('index.html', articles=all_articles)

def fetch_articles_async():
    news18_thread = Thread(target=scrape_news18_articles)
    hindu_thread = Thread(target=fetch_thehindu_headlines)

    news18_thread.start()
    hindu_thread.start()

    news18_thread.join()
    hindu_thread.join()

if __name__ == "__main__":
    app.run(debug=True)
