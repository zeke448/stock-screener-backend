from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
from datetime import datetime, timedelta
import os
from polygon import RESTClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

client = RESTClient(POLYGON_API_KEY)

def fetch_stock_data():
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    five_days_ago = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")

    tickers = ["AAPL", "GME", "TSLA", "AMC", "NVDA", "PLTR"]
    matched = []
    near_match = []

    for ticker in tickers:
        try:
            aggs_today = client.get_aggs(ticker, 1, "day", today, today)
            aggs_yesterday = client.get_aggs(ticker, 1, "day", yesterday, yesterday)

            if not aggs_today or not aggs_yesterday:
                continue

            today_data = aggs_today[0]
            yesterday_data = aggs_yesterday[0]

            price = today_data.close
            volume = today_data.volume
            avg_volume = (today_data.volume + yesterday_data.volume) / 2
            volume_ratio = volume / avg_volume if avg_volume else 0
            percent_change = ((price - yesterday_data.close) / yesterday_data.close) * 100

            ticker_details = client.get_ticker_details(ticker)
            float_shares = ticker_details.share_class_shares_outstanding or 0

            history_raw = client.get_aggs(ticker, 1, "day", five_days_ago, today)
            price_history = [round(bar.close, 2) for bar in history_raw][:5]

            stock_data = {
                "ticker": ticker,
                "price": round(price, 2),
                "volumeRatio": round(volume_ratio, 2),
                "float": float_shares,
                "percentChange": round(percent_change, 2),
                "news": fetch_news(ticker),
                "history": price_history
            }

            # Main strict filters
            if (
                1 <= price <= 20 and
                1 <= volume_ratio <= 5 and
                float_shares <= 1_000_000 and
                percent_change >= 10
            ):
                matched.append(stock_data)
            else:
                near_match.append(stock_data)

        except Exception as e:
            print(f"Error with {ticker}: {e}")
            continue

    return {
        "matched": matched,
        "nearMatch": near_match
    }

def fetch_news(ticker):
    url = f"https://newsapi.org/v2/everything?q={ticker}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        articles = response.json().get("articles", [])
        return articles[0]["title"] if articles else "No news found"
    except:
        return "Failed to fetch news"

@app.get("/api/stocks")
def get_stocks():
    return fetch_stock_data()
