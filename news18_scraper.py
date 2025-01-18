
import requests
from bs4 import BeautifulSoup
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words

# Function to scrape article content, time, and image (used only for summarization)
def scrape_article_content(article_url):
    # Send HTTP request to the article page
    response = requests.get(article_url)
    
    # Parse the content with BeautifulSoup
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Find the article tag (without worrying about class name)
    article_content = soup.find("article")
    
    # Extract the time from the article page
    time = soup.find("time")
    article_time = time.text.strip() if time else "Unknown"
    
    # Extract the image link from the article page (inside figure tag -> img tag)
    image_tag = article_content.find("figure").find("img") if article_content else None
    article_image = image_tag["src"] if image_tag else None
    
    # Check if the article content was found
    if article_content:
        # Extract all paragraphs from the article
        paragraphs = article_content.find_all("p")
        # Combine the paragraphs into a single string of article text
        article_text = "\n".join([para.text.strip() for para in paragraphs])
        return article_text, article_time, article_image
    else:
        print(f"Article content not found for URL: {article_url}")
        return None, None, None

# Function to summarize article content using LSA summarizer
def summarize_article_sumy(content, max_sentences=3):
    # Prepare the content for the summarizer
    parser = PlaintextParser.from_string(content, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summarizer.stop_words = get_stop_words("english")  # Set stop words
    summary = summarizer(parser.document, max_sentences)  # Generate summary
    
    # Join the sentences in the summary and return as a string
    return " ".join(str(sentence) for sentence in summary)

# Main function to scrape News18 articles
def scrape_news18_articles():
    url = "https://www.news18.com/business/economy/"  # URL to scrape
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the main container for blog list items
    blog_list = soup.find_all("div", class_="jsx-50600299959a4159 blog_list_row")

    # Initialize an empty list to store the data
    articles = []

    # Loop through each blog item (limit to 5)
    for blog in blog_list[:7]:
        # Extract the headline
        headline = blog.find("h3", class_="jsx-50600299959a4159").text.strip()

        # Extract the link
        link = blog.find("a", class_="jsx-50600299959a4159")["href"]

        # Get the article content, time, and image (just to summarize it)
        article_content, article_time, article_image = scrape_article_content(link)

        # Generate a summary using LSA summarizer
        if article_content:
            summary = summarize_article_sumy(article_content)  # Summarize using LSA
            source = 'News18'  # Extract source name from the link

            # Append the article data without the full content
            articles.append({
                "headline": headline,
                "link": link,
                "time": article_time,  # Use the time scraped from the article
                "summary": summary,
                "source": source,
                "image": article_image  # Add image URL to the article data
            })

    return articles

# If this script is run directly, perform a sample scrape and print results
if __name__ == "__main__":
    articles = scrape_news18_articles()
    for article in articles:
        print(f"Headline: {article['headline']}")
        print(f"Link: {article['link']}")
        print(f"Time: {article['time']}")
        print(f"Summary: {article['summary']}")
        print(f"Source: {article['source']}")
        print(f"Image: {article['image']}")
        print("-" * 40)
