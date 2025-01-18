
from flask import Flask, render_template
from hindu2 import fetch_thehindu_headlines
from mint__scraper import MintScraper
from news18_scraper import scrape_news18_articles
from financial_scraper import scrape_financial_news
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

nltk.download("punkt")
app = Flask(__name__)

# Fetch articles from all sources
def fetch_all_articles():
    # Fetch articles from The Hindu Business Line
    hindu_articles = fetch_thehindu_headlines()

    # Fetch articles from LiveMint
    mint_scraper = MintScraper()
    mint_articles = mint_scraper.scrape_mint()

    # Fetch articles from News18
    news18_articles = scrape_news18_articles()

    # Fetch articles from Financial Express
    financial_articles = scrape_financial_news()

    # Combine all articles from different sources
    all_articles = hindu_articles + mint_articles + news18_articles + financial_articles

    return all_articles


# Route to display the articles
@app.route('/')
def display_articles():
    articles = fetch_all_articles()
    return render_template('index.html', articles=articles)


# Main function to run the app
if __name__ == "__main__":
    # Start the app and display the address to paste in browser
    app.run(debug=True)

