

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer


class MintScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.headers = {"User-Agent": self.ua.random}
        self.source_name = "LiveMint"

    def scrape_mint(self):
        """
        Scrape Mint's economy section and return the article data.

        :return: List of articles with title, link, time, summary, and image
        """
        url = "https://www.livemint.com/economy"
        articles = self._scrape_generic(url, "div", "listingNew", "h2", "a", prefix="https://www.livemint.com")
        return articles

    def _scrape_generic(self, url, parent_tag, parent_class, title_tag, link_tag, prefix=""):
        """
        Generic scraping function to extract article titles, links, and summaries.

        :param url: The URL to scrape
        :param parent_tag: The parent HTML tag containing the article data
        :param parent_class: The class of the parent tag
        :param title_tag: The tag that holds the article title
        :param link_tag: The tag that contains the link to the article
        :param prefix: Prefix URL if the links are relative
        :return: List of articles with title, link, time, summary, and image
        """
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        articles = []

        print(f"Response Status for {url}: {response.status_code}")

        # Handle HTTP error if access is denied
        if response.status_code == 403:
            print(f"Access denied when trying to scrape {url}.")
            return articles

        # Extract article details
        for item in soup.find_all(parent_tag, class_=parent_class)[:7]:
            title_elem = item.find(title_tag)
            link_elem = item.find(link_tag, href=True)
            time_elem = item.find("span", {"id": lambda x: x and x.startswith("tListBox_")})  # Extract updated time
            image_elem = item.find("figure")  # Find the figure tag for the image

            if title_elem and link_elem:
                headline = title_elem.text.strip()
                link = prefix + link_elem["href"] if prefix else link_elem["href"]
                time = time_elem.text.strip() if time_elem else "Unknown time"  # Fetch updated time if available
                image = self.scrape_image(link)  # Scrape image for each article

                # Summarize the article
                summary_data = self.summarize_article(link)

                articles.append({
                    "headline": headline,
                    "link": link,
                    "time": time,
                    "summary": summary_data['summary'],
                    "source": self.source_name,
                    "image": image  # Include image URL
                })

        return articles

    def scrape_image(self, url):
        """
        Scrape the image URL from the article page.

        :param url: The URL of the article
        :return: Image URL if found, else None
        """
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")

        # Try to find the figure tag and the img tag inside it
        figure_tag = soup.find("figure",)
        if figure_tag:
            img_tag = figure_tag.find("img")
            if img_tag:
                img_url = img_tag.get("src")  # Extract image URL from src attribute
                return img_url
        return None

    def summarize_article(self, url):
        """
        Summarize the content of an article.

        :param url: URL of the article to summarize
        :return: A dictionary containing the full content and a brief summary
        """
        response = requests.get(url, headers=self.headers)
        soup = BeautifulSoup(response.content, "html.parser")
        paragraphs = soup.find_all("p")

        content = " ".join([p.text.strip() for p in paragraphs])

        # Summarize content using LexRankSummarizer
        parser = PlaintextParser.from_string(content, Tokenizer("english"))
        summarizer = LexRankSummarizer()
        summary = summarizer(parser.document, 3)  # Summarize into 3 sentences

        summary_text = " ".join(str(sentence) for sentence in summary)

        return {"content": content, "summary": summary_text}

    def display_articles(self, articles):
        """
        Display the articles' title, summary, time, link, source, and image.

        :param articles: List of article dictionaries
        """
        if not articles:
            print("No articles found.")
        for article in articles:
            print(f"Headline: {article['headline']}")
            print(f"Link: {article['link']}")
            print(f"Time: {article['time']}")
            print(f"Summary: {article['summary']}")
            print(f"Source: {article['source']}")
            print(f"Image: {article['image']}")
            print("-" * 80)


if __name__ == "__main__":
    scraper = MintScraper()
    articles = scraper.scrape_mint()  # Scrape Mint articles
    scraper.display_articles(articles)  # Display the articles
