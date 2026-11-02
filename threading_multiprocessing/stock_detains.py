import yfinance as yf
import os
import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from dotenv import load_dotenv

MAX_WORKERS = 10

# Load environment variables
script_dir = Path(__file__).resolve().parent
load_dotenv(script_dir / ".env")

# Resolve TIMES_PATH
times_path = os.getenv("TIMES_PATH", "bitcoin_dates.txt")
if not os.path.isabs(times_path) and not os.path.exists(times_path):
    times_path = str(script_dir / times_path)

destination_file = os.getenv("DESTINATION_FILE", "bitcoin_data.csv")
if not os.path.isabs(destination_file):
    destination_file = str(script_dir / destination_file)

try:
    with open(times_path, "r") as f:
        timestamps = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print(f"File not found: {times_path}")
    exit(1)


def fetch_stock_data(timestamp, ticker="BTC-USD", stock_type="Bitcoin"):
    """
    Fetches hourly stock data for a given timestamp and calculates percentage change.
    """
    dt = datetime.datetime.fromisoformat(timestamp.strip())
    start = dt.replace(minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(hours=1)

    stock = yf.Ticker(ticker)
    data = stock.history(start=start, end=end, interval="1h")

    if data.empty:
        return {
            "hour": timestamp,
            "stock type": stock_type,
            "percentage change": None,
        }

    open_price = float(data["Open"].iloc[0])
    close_price = float(data["Close"].iloc[0])
    percentage_change = ((close_price - open_price) / open_price) * 100

    return {
        "hour": timestamp,
        "stock type": stock_type,
        "percentage change": percentage_change,
    }


def main():
    results = []
    print(f"Fetching data for {len(timestamps)} timestamps using {MAX_WORKERS} workers...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_timestamp = {
            executor.submit(fetch_stock_data, timestamp, "BTC-USD", "Bitcoin"): timestamp
            for timestamp in timestamps
        }

        for future in as_completed(future_to_timestamp):
            timestamp = future_to_timestamp[future]
            try:
                result = future.result()
                results.append(result)
                print(result)
            except Exception as exc:
                print(f"{timestamp} generated an exception: {exc}")

    if results:
        df = pd.DataFrame(results)
        df.to_csv(destination_file, index=False)
        print(f"Saved {len(results)} rows to {destination_file}")


if __name__ == "__main__":
    main()
