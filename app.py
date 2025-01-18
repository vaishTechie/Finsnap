from flask import Flask, render_template, jsonify
import time
import logging
from financial_express_scraper import scrape_financial_news  # Assuming the scraper functions are in financial_express_scraper.py

# Initialize the Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Route to display the homepage
@app.route('/')
def index():
    try:
        # Scrape the financial news
        articles = scrape_financial_news()
        
        # Pass the scraped articles to the template
        return render_template('index.html', articles=articles)
    
    except Exception as e:
        logging.error(f"Error loading homepage: {str(e)}")
        return "Error loading articles", 500

# Route to fetch news articles as JSON (for API)
@app.route('/api/news', methods=['GET'])
def get_news():
    try:
        # Scrape the financial news
        articles = scrape_financial_news()

        # Return articles as JSON
        return jsonify(articles)
    
    except Exception as e:
        logging.error(f"Error fetching articles API: {str(e)}")
        return jsonify({"error": "Error fetching articles"}), 500

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)
