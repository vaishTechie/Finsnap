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
    for blog in blog_list[:8]:
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

# Fetch article details from The Hindu
def fetch_article_details(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        paragraphs = soup.find_all('p')
        article_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        time_tag = soup.find('div', class_='bl-by-line')
        time = None

        if time_tag:
            time_text = time_tag.get_text(strip=True)
            time = time_text.split('|')[0].strip()

        if not time:
            time = "No time available"

        return article_content, time

    except Exception as e:
        print(f"Error fetching article details: {str(e)}")
        return None, "No time available"

# Fetch image from The Hindu article
def fetch_image_from_article(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

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

# Fetch articles from The Hindu Business Line
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
                        "summary": article_content[:500],
                        "time": time,
                        "image": image_url,
                        "source": "The Hindu Business Line"
                    })
    return articles

# Fetch articles asynchronously
def fetch_articles_async():
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_news18 = executor.submit(scrape_news18_articles)
        future_hindu = executor.submit(fetch_thehindu_headlines)
        
        news18_articles = future_news18.result()
        hindu_articles = future_hindu.result()

    return news18_articles + hindu_articles

# Flask route to serve all scraped data
@app.route('/')
def index():
    all_articles = fetch_articles_async()
    return render_template('index.html', articles=all_articles)

# Run the app
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
