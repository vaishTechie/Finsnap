import os
import nltk
from flask import Flask, render_template, jsonify
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

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

# Mint Scraper Functions (same as News18, but with Mint's logic and selectors)
class MintScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.headers = {"User-Agent": self.ua.random}
        self.source_name = "LiveMint"

    def scrape_mint(self):
        """
        Scrape Mint's economy section and return the article data.
        """
        url = "https://www.livemint.com/economy"
        articles = self._scrape_generic(url, "div", "listingNew", "h2", "a", prefix="https://www.livemint.com")
        return articles

    def _scrape_generic(self, url, parent_tag, parent_class, title_tag, link_tag, prefix=""):
        """
        Generic scraping function to extract article titles, links, and summaries.
        """
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        articles = []

        # Extract article details
        for item in soup.find_all(parent_tag, class_=parent_class)[:5]:
            title_elem = item.find(title_tag)
            link_elem = item.find(link_tag, href=True)
            time_elem = item.find("span", {"id": lambda x: x and x.startswith("tListBox_")})  # Extract updated time
            image_elem = item.find("figure")  # Find the figure tag for the image

            if title_elem and link_elem:
                headline = title_elem.text.strip()
                link = prefix + link_elem["href"] if prefix else link_elem["href"]
                time = time_elem.text.strip() if time_elem else "Unknown time"  # Fetch updated time if available
                image = self.scrape_image(link)  # Scrape image for each article

                # Use the first 500 characters as summary
                summary = self.summarize_article(link)['summary']

                articles.append({
                    "headline": headline,
                    "link": link,
                    "time": time,
                    "summary": summary,  # Use simple summary
                    "source": self.source_name,
                    "image": image  # Include image URL
                })

        return articles

    def scrape_image(self, url):
        """
        Scrape the image URL from the article page.
        """
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")

        figure_tag = soup.find("figure",)
        if figure_tag:
            img_tag = figure_tag.find("img")
            if img_tag:
                img_url = img_tag.get("src")
                return img_url
        return None

    def summarize_article(self, url):
        """
        Summarize the content of an article by taking the first 500 characters.
        """
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")

        content = " ".join([p.text.strip() for p in paragraphs])

        # Simple summary (first 500 characters)
        return {"content": content, "summary": content[:500]}


# Flask Route to serve all scraped data
@app.route('/')
def index():
    # Fetch articles from News18
    news18_articles = scrape_news18_articles()

    # Fetch articles from Mint
    mint_scraper = MintScraper()
    mint_articles = mint_scraper.scrape_mint()

    # Combine both articles
    all_articles = news18_articles + mint_articles

    # Render the HTML template and pass the articles to it
    return render_template('index.html', articles=all_articles)


if __name__ == "__main__":
    app.run(debug=True)
