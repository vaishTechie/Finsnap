
import os
from flask import Flask, jsonify, render_template
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words
import random




app = Flask(__name__)

# Helper function to make requests and parse HTML
def make_request(url, headers=None):
    try:
        if headers is None:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
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

        parser = PlaintextParser.from_string(content, Tokenizer("english"))
        summarizer = LexRankSummarizer()
        summary = summarizer(parser.document, 3)

        summary_text = " ".join(str(sentence) for sentence in summary)

        return {"content": content, "summary": summary_text}

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

def summarize_article_sumy(content, max_sentences=3):
    parser = PlaintextParser.from_string(content, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summarizer.stop_words = get_stop_words("english")
    summary = summarizer(parser.document, max_sentences)
    return " ".join(str(sentence) for sentence in summary)

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
            summary = summarize_article_sumy(article_content)
            articles.append({
                "headline": headline,
                "link": link,
                "time": article_time,
                "summary": summary,
                "source": "News18",
                "image": article_image
            })

    return articles

# The Hindu Business Line Scraper Functions
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
                    summary = summarize_article_sumy(article_content)
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

#financial_express 
def make_request(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for invalid responses
        return BeautifulSoup(response.content, 'html.parser')
    except Exception as e:
        print(f"Error fetching URL {url}: {str(e)}")
        return None

# Fetch Financial Express headlines
def fetch_financial_express_headlines(url, limit=7):
    try:
        soup = make_request(url)
        if soup is None:
            return []

        headlines = []
        articles = soup.find_all('article', id=True, limit=limit)

        for article in articles:
            entry_wrapper = article.find('div', class_='entry-wrapper')
            headline_text = headline_url = headline_time = 'Not available'

            if entry_wrapper:
                entry_title_div = entry_wrapper.find('div', class_='entry-title')
                headline_tag = entry_title_div.find('a') if entry_title_div else None
                headline_text = headline_tag.get_text(strip=True) if headline_tag else 'No headline available'
                headline_url = headline_tag['href'] if headline_tag else 'No URL available'

                entry_meta = entry_wrapper.find('div', class_='entry-meta')
                if entry_meta:
                    time_tag = entry_meta.find('time', class_='entry-date published')
                    headline_time = time_tag.get_text(strip=True) if time_tag else 'No time available'

            headlines.append({
                'headline': headline_text,
                'time': headline_time,
                'link': headline_url,
                'source': 'Financial Express'
            })

        return headlines

    except Exception as e:
        print(f"Error fetching headlines: {str(e)}")
        return []

# Fetch image from the article page
def scrape_image(url):
    try:
        soup = make_request(url)
        if soup is None:
            return 'No image found'

        image_div = soup.find('div', class_='image-with-overlay')
        if image_div:
            img_tag = image_div.find('img')
            if img_tag:
                return img_tag['src']

        return 'No image found'

    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return 'No image found'

# Fetch article content for summarization
def fetch_article_content(url):
    try:
        soup = make_request(url)
        if soup is None:
            return 'Error fetching article content'

        article_section = soup.find('div', class_='article-section')
        if article_section:
            content_div = article_section.find('div', class_='post-content wp-block-post-content mb-4')
            if content_div:
                pcl_container = content_div.find('div', class_='pcl-container')
                if pcl_container:
                    paragraphs = pcl_container.find_all('p')
                    return ' '.join([para.get_text() for para in paragraphs])

        return 'Content not available'

    except Exception as e:
        print(f"Error fetching article content: {str(e)}")
        return 'Error fetching article content'

# Summarize article content using LexRankSummarizer
def summarize_article(content):
    parser = PlaintextParser.from_string(content, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    summary = summarizer(parser.document, 3)  # Summarize into 3 sentences
    return " ".join(str(sentence) for sentence in summary)

# Main function to scrape and return articles in the required format
def scrape_financial_news():
    url = 'https://www.financialexpress.com/about/economy/'

    try:
        headlines = fetch_financial_express_headlines(url)
        if not headlines:
            print("No headlines found.")
            return []

        articles = []
        for headline_info in headlines:
            article_content = fetch_article_content(headline_info['link'])
            if article_content.startswith("Error"):
                print(f"Error fetching article content for {headline_info['headline']}.")
                continue

            image = scrape_image(headline_info['link'])
            summary = summarize_article(article_content)

            # Append the article data in dictionary format
            articles.append({
                "headline": headline_info['headline'],
                "link": headline_info['link'],
                "time": headline_info['time'],
                "summary": summary,
                "source": headline_info['source'],
                "image": image
            })

        return articles

    except Exception as e:
        print(f"Error during scraping: {str(e)}")
        return []




# Flask Route to serve all scraped data
@app.route('/')
def index():
    # Fetch articles
    mint_scraper = MintScraper()
    mint_articles = mint_scraper.scrape_mint()

    hindu_articles = fetch_thehindu_headlines()
    news18_articles = scrape_news18_articles()
    financial_articles = scrape_financial_news()

    # Combine all articles
    all_articles = mint_articles + hindu_articles + news18_articles + financial_articles

    # Shuffle the articles to display them in random order
    random.shuffle(all_articles)

    # Render the HTML template and pass the articles to it
    return render_template('index.html', articles=all_articles)
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    app.run(debug=True)
