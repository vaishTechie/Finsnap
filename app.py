import os
import requests
from flask import Flask, render_template
from bs4 import BeautifulSoup
from threading import Thread
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

app = Flask(__name__)

# Helper function to make requests and parse HTML
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

# Scrape article content (helper function)
def scrape_article_content(article_url):
    response = requests.get(article_url, timeout=10)
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

# Fetch articles from News18
def scrape_news18_articles():
    url = "https://www.news18.com/business/economy/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    blog_list = soup.find_all("div", class_="jsx-50600299959a4159 blog_list_row")
    articles = []
    for blog in blog_list[:10]:
        headline = blog.find("h3", class_="jsx-50600299959a4159").text.strip()
        link = blog.find("a", class_="jsx-50600299959a4159")["href"]
        article_content, article_time, article_image = scrape_article_content(link)
        if article_content:
            summary = article_content[:500]
            articles.append({
                "headline": headline,
                "link": link,
                "time": article_time,
                "summary": summary,
                "source": "News18",
                "image": article_image
            })
    return articles





# Fetch articles asynchronously
def fetch_articles_async():
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_news18 = executor.submit(scrape_news18_articles)

        
        news18_articles = future_news18.result()
    

    return news18_articles 

# Flask route to serve all scraped data
@app.route('/')
def index():
    all_articles = fetch_articles_async()
    return render_template('index.html', articles=all_articles)

# Run the app
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
