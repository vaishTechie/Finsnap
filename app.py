import os
import nltk
from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re

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

# Simple summarizer: Truncate the content to the first 500 characters
def summarize_article_simple(content, char_limit=500):
    return content[:char_limit]

# News18 Scraper Functions
def scrape_news18_article_content(article_url):
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
    return None, None, None

def scrape_news18_articles():
    url = "https://www.news18.com/business/economy/"
    soup = make_request(url)
    if not soup:
        return []
    
    blog_list = soup.find_all("div", class_="jsx-50600299959a4159 blog_list_row")
    articles = []
    
    for blog in blog_list[:8]:
        headline = blog.find("h3", class_="jsx-50600299959a4159").text.strip()
        link = blog.find("a", class_="jsx-50600299959a4159")["href"]
        article_content, article_time, article_image = scrape_news18_article_content(link)
        
        if article_content:
            summary = summarize_article_simple(article_content)
            articles.append({
                "headline": headline,
                "link": link,
                "time": article_time,
                "summary": summary,
                "source": "News18",
                "image": article_image
            })
    return articles

# Hindu Business Line Scraper Functions
def clean_article_content(content):
    # Remove extra whitespace and normalize spacing
    content = re.sub(r'\s+', ' ', content)
    return content.strip()

def fetch_hindu_article_details(url):
    soup = make_request(url)
    if not soup:
        return None, None, None
    
    paragraphs = soup.find_all('p')
    article_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
    article_content = clean_article_content(article_content)
    
    time_tag = soup.find('div', class_='bl-by-line')
    time = time_tag.get_text(strip=True).split('|')[0].strip() if time_tag else "Unknown"
    
    image_div = soup.find('div', class_='picture-big ratio ratio-16x9')
    image_url = None
    if image_div:
        source_tags = image_div.find_all('source')
        if source_tags:
            largest_image_url = source_tags[-1].get('srcset')
            if largest_image_url and not largest_image_url.startswith('http'):
                largest_image_url = 'https://bl-i.thgim.com' + largest_image_url
            image_url = largest_image_url
            
    return article_content, time, image_url

def scrape_hindu_articles():
    url = "https://www.thehindubusinessline.com/economy/"
    soup = make_request(url)
    if not soup:
        return []
    
    headlines_list = soup.find("ul", class_="section-result-list")
    articles = []
    
    if headlines_list:
        for item in headlines_list.find_all("li", itemprop="itemListElement")[:8]:
            headline_tag = item.find("h3", class_="title")
            link_tag = item.find("a", itemprop="url")
            
            if headline_tag and link_tag:
                headline = headline_tag.get_text(strip=True)
                link = link_tag['href']
                if not link.startswith("http"):
                    link = "https://www.thehindubusinessline.com" + link
                
                article_content, time, image_url = fetch_hindu_article_details(link)
                if article_content:
                    summary = summarize_article_simple(article_content)  # Using simple summarization
                    articles.append({
                        "headline": headline,
                        "link": link,
                        "summary": summary,
                        "time": time,
                        "image": image_url,
                        "source": "The Hindu Business Line"
                    })
    return articles

# Flask Routes
@app.route('/')
def index():
    # Fetch articles from both sources
    news18_articles = scrape_news18_articles()
    hindu_articles = scrape_hindu_articles()
    
    # Combine all articles
    all_articles = news18_articles + hindu_articles
    
    # Render the HTML template with all articles
    return render_template('index.html', articles=all_articles)

if __name__ == "__main__":
    app.run(debug=True)
