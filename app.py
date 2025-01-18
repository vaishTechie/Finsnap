# import nltk
# import os
# import logging
# from flask import Flask, jsonify, request, render_template
# from financial_scraper import fetch_financial_express_headlines, fetch_article_content, summarize_article, scrape_image
# from mint__scraper import MintScraper
# from hindu2 import fetch_thehindu_headlines, fetch_image_from_article
# from news18_scraper import scrape_news18_articles
# import random
# import nltk

# nltk.download('punkt_tab')


# # Set up logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)



# def standardize_article(article, include_image=True):
#     return {
#         "headline": article.get("headline", "No headline available."),
#         "summary": article.get("summary", "No summary available."),
#         "link": article.get("link", ""),
#         "source": article.get("source", "Unknown"),
#         "time": article.get("time", "No time available"),
#         "image": article.get("image", "No image available") if include_image else "No image available"
#     }

# def create_app():
#     app = Flask(__name__)
#     app.config['TIMEOUT'] = 120
    
#     @app.route('/')
#     def home():
#         try:
#             # Fetch articles from Financial Express
#             financial_articles = fetch_financial_express_headlines("https://www.financialexpress.com/about/economy/")
#             # Fetch articles from Mint
#             mint_articles = MintScraper().scrape_mint()
#             # Fetch articles from Hindu
#             hindu_articles = fetch_thehindu_headlines()
#             # Fetch articles from News18
#             news18_articles = scrape_news18_articles()

#             # Process Financial Express articles
#             for article in financial_articles:
#                 article_url = article['link']
#                 article_content = fetch_article_content(article_url)
#                 if article_content and article_content != 'Error fetching article content':
#                     summary = summarize_article(article_content)
#                     article['summary'] = summary
#                 article['image'] = scrape_image(article_url)

#             # Process Hindu articles
#             for article in hindu_articles:
#                 article_image = fetch_image_from_article(article['link'])
#                 article['image'] = article_image

#             # Standardize all articles
#             all_articles = [standardize_article(article, include_image=True) for article in hindu_articles]
#             all_articles += [standardize_article(article) for article in financial_articles + mint_articles + news18_articles]

#             # Shuffle articles
#             random.shuffle(all_articles)
            
#             logger.info(f"Successfully fetched {len(all_articles)} articles")
#             return render_template('index.html', articles=all_articles)

#         except Exception as e:
#             logger.error(f"Error in home route: {str(e)}")
#             return jsonify({"error": str(e)}), 500

#     @app.route('/financial', methods=['GET'])
#     def get_financial_news():
#         try:
#             headlines = fetch_financial_express_headlines("https://www.financialexpress.com/about/economy/")
#             for article in headlines:
#                 article_url = article['url']
#                 article_content = fetch_article_content(article_url)
#                 if article_content and article_content != 'Error fetching article content':
#                     article['summary'] = summarize_article(article_content)
#                 article['image'] = scrape_image(article_url)
#             return jsonify(headlines)
#         except Exception as e:
#             logger.error(f"Error in financial news route: {str(e)}")
#             return jsonify({"error": str(e)}), 500

#     @app.route('/financial/article', methods=['POST'])
#     def get_financial_article_summary():
#         data = request.json
#         url = data.get('url')

#         if not url:
#             return jsonify({"error": "Missing 'url' in request body."}), 400

#         try:
#             content = fetch_article_content(url)
#             summary = summarize_article(content)
#             return jsonify({"content": content, "summary": summary})
#         except Exception as e:
#             logger.error(f"Error in article summary route: {str(e)}")
#             return jsonify({"error": str(e)}), 500

#     @app.route('/mint', methods=['GET'])
#     def get_mint_news():
#         try:
#             scraper = MintScraper()
#             articles = scraper.scrape_mint()
#             return jsonify(articles)
#         except Exception as e:
#             logger.error(f"Error in mint news route: {str(e)}")
#             return jsonify({"error": str(e)}), 500

#     @app.route('/hindu', methods=['GET'])
#     def get_hindu_news():
#         try:
#             articles = fetch_thehindu_headlines()
#             for article in articles:
#                 article['image'] = fetch_image_from_article(article['link'])
#             return jsonify(articles)
#         except Exception as e:
#             logger.error(f"Error in hindu news route: {str(e)}")
#             return jsonify({"error": str(e)}), 500

#     @app.route('/news18', methods=['GET'])
#     def get_news18_articles():
#         try:
#             articles = scrape_news18_articles()
#             return jsonify(articles)
#         except Exception as e:
#             logger.error(f"Error in news18 route: {str(e)}")
#             return jsonify({"error": str(e)}), 500

#     return app

# def start_app():
#     app = create_app()
#     return app

# if __name__ == "__main__":
#     app = start_app()
#     app.run(debug=True)
from flask import Flask, render_template
from hindu2 import fetch_thehindu_headlines
from mint__scraper import MintScraper
from news18_scraper import scrape_news18_articles
from financial_scraper import scrape_financial_news

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

