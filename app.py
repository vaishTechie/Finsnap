from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import os

# Load environment variables from .env
load_dotenv()
# Update the app.run() at the bottom
if _name_ == "_main_":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
if not os.path.exists(os.path.join(nltk.data.path[0], 'tokenizers/punkt')):
    nltk.download('punkt')

# Ensure the punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Ensure you have downloaded the necessary NLTK data files
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')



app = Flask(__name__)

# Fetch user-agent from environment variable
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")


# Helper function to make requests and parse HTML
def make_request(url, headers=None):
    try:
        if headers is None:
            headers = {"User-Agent": USER_AGENT}
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for invalid responses
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL {url}: {str(e)}")
        return None

# Mint Scraper Class
class MintScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.headers = {"User-Agent": self.ua.random}
        self.source_name = "LiveMint"

    def scrape_mint(self):
        url = "https://www.livemint.com/economy"
        articles = self._scrape_generic(url, "div", "listingNew", "h2", "a", prefix="https://www.livemint.com")
        return articles

    def _scrape_generic(self, url, parent_tag, parent_class, title_tag, link_tag, prefix=""):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        articles = []

        if response.status_code == 403:
            print(f"Access denied when trying to scrape {url}.")
            return articles

        for item in soup.find_all(parent_tag, class_=parent_class)[:7]:
            title_elem = item.find(title_tag)
            link_elem = item.find(link_tag, href=True)
            time_elem = item.find("span", {"id": lambda x: x and x.startswith("tListBox_")})
            image_elem = item.find("figure")

            if title_elem and link_elem:
                headline = title_elem.text.strip()
                link = prefix + link_elem["href"] if prefix else link_elem["href"]
                time = time_elem.text.strip() if time_elem else "Unknown time"
                image = self.scrape_image(link)

                summary_data = self.summarize_article(link)

                articles.append({
                    "headline": headline,
                    "link": link,
                    "time": time,
                    "summary": summary_data['summary'],
                    "source": self.source_name,
                    "image": image
                })

        return articles

    def scrape_image(self, url):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")

        figure_tag = soup.find("figure")
        if figure_tag:
            img_tag = figure_tag.find("img")
            if img_tag:
                img_url = img_tag.get("src")
                return img_url
        return None

    def summarize_article(self, url):
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")

        content = " ".join([p.text.strip() for p in paragraphs])

        # Summarization logic here, can be done with the existing Summarizer
        return {"content": content, "summary": content[:200]}  # Simple summarization for demonstration

# News18 Scraper Functions
def scrape_article_content(article_url):
    response = requests.get(article_url)
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

# Scrape News18
def scrape_news18_articles():
    url = "https://www.news18.com/business/economy/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    blog_list = soup.find_all("div", class_="jsx-50600299959a4159 blog_list_row")
    articles = []

    for blog in blog_list[:7]:
        headline = blog.find("h3", class_="jsx-50600299959a4159").text.strip()
        link = blog.find("a", class_="jsx-50600299959a4159")["href"]

        article_content, article_time, article_image = scrape_article_content(link)

        if article_content:
            summary = article_content[:200]  # Simple summary for demo
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
def fetch_thehindu_headlines():
    url = "https://www.thehindubusinessline.com/economy/"
    soup = make_request(url)
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
                    summary = article_content[:200]  # Simple summary for demo
                    image_url = fetch_image_from_article(link)

                    articles.append({
                        "headline": headline,
                        "link": link,
                        "summary": summary,
                        "time": time,
                        "image": image_url,
                        "source": "The Hindu Business Line"
                    })

    return articles

def fetch_article_details(url):
    try:
        soup = make_request(url)
        paragraphs = soup.find_all('p')
        article_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        time_tag = soup.find('div', class_='bl-by-line')
        time = None
        if time_tag:
            time_text = time_tag.get_text(strip=True)
            time = time_text.split('|')[0].strip()

        return article_content, time if time else "No time available"
    except Exception as e:
        print(f"Error fetching article details: {str(e)}")
        return None, "No time available"

def fetch_image_from_article(url):
    soup = make_request(url)
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

# Fetch all articles concurrently using ThreadPoolExecutor
def fetch_all_articles():
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(MintScraper().scrape_mint),
            executor.submit(fetch_thehindu_headlines),
            executor.submit(scrape_news18_articles)
        ]
        articles = []
        for future in futures:
            articles.extend(future.result())
        return articles

@app.route('/')
def index():
    all_articles = fetch_all_articles()
    return render_template('index.html', articles=all_articles)

if _name_ == "_main_":
    app.run(debug=True)
    
