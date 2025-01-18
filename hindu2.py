

import requests
from bs4 import BeautifulSoup
import re
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.utils import get_stop_words

# Function to clean article content
def clean_article_content(content):
    content = re.sub(r'[0-9]+(?:\.[0-9]+)?', '', content)  # Remove numbers
    content = re.sub(r'[^\w\s.,;:!?]', '', content)  # Remove special characters except punctuation
    content = re.sub(r'\s+', ' ', content)  # Remove extra whitespace
    return content.strip()

# Function to summarize article content using Sumy
def summarize_article_sumy(content, max_sentences=3):
    parser = PlaintextParser.from_string(content, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summarizer.stop_words = get_stop_words("english")
    summary = summarizer(parser.document, max_sentences)
    return " ".join(str(sentence) for sentence in summary)

# Function to fetch article details
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

        # Clean content for summarization
        article_content = clean_article_content(article_content)

        # Extract publication time (if available)
        time_tag = soup.find('div', class_='bl-by-line')
        time = None

        if time_tag:
            # Extract the date and time part (before the location)
            time_text = time_tag.get_text(strip=True)
            time = time_text.split('|')[0].strip()  # Get the part before the location

        if not time:
            time = "No time available"

        return article_content, time

    except Exception as e:
        print(f"Error fetching article details: {str(e)}")
        return None, "No time available"

# Function to fetch image from headline page
# Function to fetch image from the article page
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
            # Find all source tags within the picture element
            source_tags = image_div.find_all('source')
            if source_tags:
                # Extract the largest resolution image from the srcset attribute
                largest_image_url = source_tags[-1].get('srcset')  # Get the last source (usually the highest resolution)

                # If the URL is relative, complete it with the base URL
                if largest_image_url and not largest_image_url.startswith('http'):
                    largest_image_url = 'https://bl-i.thgim.com' + largest_image_url
                
                image_url = largest_image_url

        return image_url

    except Exception as e:
        print(f"Error fetching image from article: {str(e)}")
        return None


    except Exception as e:
        print(f"Error fetching image: {str(e)}")
        return None

# Function to fetch headlines from The Hindu Business Line
def fetch_thehindu_headlines():
    url = "https://www.thehindubusinessline.com/economy/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # Locate the headlines list
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
                
                # Fetch article details
                article_content, time = fetch_article_details(link)
                if article_content:
                    # Generate summary using Sumy
                    summary = summarize_article_sumy(article_content)

                    # Fetch image from the headline page
                    image_url = fetch_image_from_article(link)

                    articles.append({
                        "headline": headline,
                        "link": link,
                        "summary": summary,
                        "time": time,
                        "image": image_url,  # Adding image URL
                        "source": "The Hindu Business Line"  # Adding source name
                    })

    return articles

# Function to display the results
def display_results(articles):
    for article in articles:
        print(f"Headline: {article['headline']}")
        print(f"Link: {article['link']}")
        print(f"Published: {article['time']}")
        print(f"Summary: {article['summary']}")
        print(f"Image: {article['image']}")
        print(f"Source: {article['source']}")
        print("-" * 80)

# Main entry point
if __name__ == "__main__":
    articles = fetch_thehindu_headlines()
    display_results(articles)
