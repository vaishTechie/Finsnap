import time
import logging
from bs4 import BeautifulSoup
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Helper function for making requests and parsing HTML
def make_request(url):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Raise an error for invalid responses
        return BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching URL {url}: {str(e)}")
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
        logging.error(f"Error fetching headlines: {str(e)}")
        return []

# Fetch content and image in one request
def scrape_article(url):
    try:
        soup = make_request(url)
        if soup is None:
            return {'content': None, 'image': None}

        # Extract content
        article_section = soup.find('div', class_='article-section')
        content = 'Content not available'
        if article_section:
            content_div = article_section.find('div', class_='post-content wp-block-post-content mb-4')
            if content_div:
                pcl_container = content_div.find('div', class_='pcl-container')
                if pcl_container:
                    paragraphs = pcl_container.find_all('p')
                    content = ' '.join([para.get_text() for para in paragraphs])

        # Extract image
        image = 'No image found'
        image_div = soup.find('div', class_='image-with-overlay')
        if image_div:
            img_tag = image_div.find('img')
            if img_tag:
                image = img_tag['src']

        return {'content': content, 'image': image}

    except Exception as e:
        logging.error(f"Error fetching article: {str(e)}")
        return {'content': None, 'image': None}

# Lead-based summarization method (quick and effective for news articles)
def summarize_article(content, num_sentences=3):
    try:
        # Split content into sentences
        sentences = content.split('. ')
        
        # Return the first few sentences as the summary
        if len(sentences) <= num_sentences:
            return content  # Return full content if it's short
        else:
            return '. '.join(sentences[:num_sentences]) + '.'
    
    except Exception as e:
        logging.error(f"Error during summarization: {str(e)}")
        return "Summary not available"

# Main function to scrape and return articles in the required format
def scrape_financial_news():
    url = 'https://www.financialexpress.com/about/economy/'
    try:
        headlines = fetch_financial_express_headlines(url)
        if not headlines:
            logging.warning("No headlines found.")
            return []

        articles = []
        for headline_info in headlines:
            article_data = scrape_article(headline_info['link'])
            if not article_data['content']:
                logging.warning(f"Content not available for {headline_info['headline']}.")
                continue

            summary = summarize_article(article_data['content'])

            # Append the article data in dictionary format
            articles.append({
                "headline": headline_info['headline'],
                "link": headline_info['link'],
                "time": headline_info['time'],
                "summary": summary,
                "source": headline_info['source'],
                "image": article_data['image']
            })

            # Add a delay to respect the website's server
            time.sleep(2)

        return articles

    except Exception as e:
        logging.error(f"Error during scraping: {str(e)}")
        return []

# If this script is run directly, perform a sample scrape and print results
if __name__ == "__main__":
    articles = scrape_financial_news()

    if articles:
        logging.info("\nFinal Articles Data:")
        for article in articles:
            print(f"📰 Headline: {article['headline']}")
            print(f"⏰ Published: {article['time']}")
            print(f"🔗 Link: {article['link']}")
            print(f"📢 Source: {article['source']}")
            print(f"🖼 Image: {article['image']}")
            print(f"Summary: {article['summary']}")
            print("-" * 40)
