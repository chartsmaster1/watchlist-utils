import requests
import pandas as pd
from io import StringIO
from datetime import datetime

API_KEY = "OFWE463Q7WHJXGAM"
url = f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={API_KEY}"

response = requests.get(url)

# Read CSV data into DataFrame
df = pd.read_csv(StringIO(response.text))

# Convert reportDate to datetime
df['reportDate'] = pd.to_datetime(df['reportDate'], errors='coerce')

# Filter for today's earnings
today = pd.Timestamp(datetime.today().date())
todays_earnings = df[df['reportDate'] == today]

print("Companies reporting earnings today:")
print(todays_earnings[['symbol', 'name', 'reportDate', 'fiscalDateEnding', 'estimate', 'currency']])
