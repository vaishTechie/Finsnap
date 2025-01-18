import os
import nltk
from flask import Flask, render_template, jsonify
from flask_cors import CORS  # Add this import
import traceback
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
import re

app = Flask(__name__)
CORS(app) 

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

# Simple summarizer
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

# Financial Express Scraper Functions
def scrape_financial_article_content(article_url):
    soup = make_request(article_url)
    if not soup:
        return None, None, None
    
    article_section = soup.find('div', class_='article-section')
    time_tag = soup.find('time', class_='entry-date published')
    article_time = time_tag.get_text(strip=True) if time_tag else "Unknown"
    
    image_div = soup.find('div', class_='image-with-overlay')
    article_image = image_div.find('img')['src'] if image_div and image_div.find('img') else None
    
    if article_section:
        content_div = article_section.find('div', class_='post-content wp-block-post-content mb-4')
        if content_div:
            pcl_container = content_div.find('div', class_='pcl-container')
            if pcl_container:
                paragraphs = pcl_container.find_all('p')
                article_text = ' '.join([para.get_text() for para in paragraphs])
                return article_text, article_time, article_image
    
    return None, None, None

def scrape_financial_articles():
    url = 'https://www.financialexpress.com/about/economy/'
    soup = make_request(url)
    if not soup:
        return []
    
    articles = []
    article_items = soup.find_all('article', id=True)[:8]
    
    for article in article_items:
        entry_wrapper = article.find('div', class_='entry-wrapper')
        if entry_wrapper:
            entry_title_div = entry_wrapper.find('div', class_='entry-title')
            headline_tag = entry_title_div.find('a') if entry_title_div else None
            
            if headline_tag:
                headline = headline_tag.get_text(strip=True)
                link = headline_tag['href']
                article_content, article_time, article_image = scrape_financial_article_content(link)
                
                if article_content:
                    summary = summarize_article_simple(article_content)
                    articles.append({
                        "headline": headline,
                        "link": link,
                        "time": article_time,
                        "summary": summary,
                        "source": "Financial Express",
                        "image": article_image
                    })
    return articles

# LiveMint Scraper Functions
def scrape_mint_article_content(article_url):
    soup = make_request(article_url)
    if not soup:
        return None, None, None
    
    paragraphs = soup.find_all("p")
    article_text = " ".join([p.text.strip() for p in paragraphs])
    
    time_elem = soup.find("span", {"id": lambda x: x and x.startswith("tListBox_")})
    article_time = time_elem.text.strip() if time_elem else "Unknown"
    
    figure_tag = soup.find("figure")
    article_image = figure_tag.find("img")['src'] if figure_tag and figure_tag.find("img") else None
    
    return article_text, article_time, article_image

def scrape_mint_articles():
    url = "https://www.livemint.com/economy"
    soup = make_request(url)
    if not soup:
        return []
    
    articles = []
    article_items = soup.find_all("div", class_="listingNew")[:8]
    
    for item in article_items:
        title_elem = item.find("h2")
        link_elem = item.find("a", href=True)
        
        if title_elem and link_elem:
            headline = title_elem.text.strip()
            link = "https://www.livemint.com" + link_elem["href"]
            article_content, article_time, article_image = scrape_mint_article_content(link)
            
            if article_content:
                summary = summarize_article_simple(article_content)
                articles.append({
                    "headline": headline,
                    "link": link,
                    "time": article_time,
                    "summary": summary,
                    "source": "LiveMint",
                    "image": article_image
                })
    return articles

# Flask Routes
@app.route('/api/articles')
def get_articles():
    try:
        # Add debug logging
        print("Starting article fetch...")
        
        # Initialize empty lists
        news18_articles = []
        financial_articles = []
        mint_articles = []
        
        # Try each scraper independently
        try:
            news18_articles = scrape_news18_articles()
            print(f"Fetched {len(news18_articles)} News18 articles")
        except Exception as e:
            print(f"Error scraping News18: {str(e)}")
            
        try:
            financial_articles = scrape_financial_articles()
            print(f"Fetched {len(financial_articles)} Financial Express articles")
        except Exception as e:
            print(f"Error scraping Financial Express: {str(e)}")
            
        try:
            mint_articles = scrape_mint_articles()
            print(f"Fetched {len(mint_articles)} LiveMint articles")
        except Exception as e:
            print(f"Error scraping LiveMint: {str(e)}")
        
        # Combine all articles
        all_articles = news18_articles + financial_articles + mint_articles
        
        # If no articles were fetched, raise an exception
        if not all_articles:
            raise Exception("No articles could be fetched from any source")
            
        print(f"Total articles fetched: {len(all_articles)}")
        
        # Return JSON response with articles
        return jsonify({
            "status": "success",
            "data": all_articles,
            "count": len(all_articles)
        })
        
    except Exception as e:
        print(f"Error in get_articles: {str(e)}")
        print(traceback.format_exc())  # Print full traceback
        return jsonify({
            "status": "error",
            "message": str(e),
            "details": traceback.format_exc()
        }), 500

@app.route('/')
def index():
    # Just render the template without articles
    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
