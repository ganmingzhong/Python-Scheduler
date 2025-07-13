import logging
import logging.handlers
import os

import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import timeit
import time

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_file_handler = logging.handlers.RotatingFileHandler(
    "status.log",
    maxBytes=1024 * 1024,
    backupCount=1,
    encoding="utf8",
)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger_file_handler.setFormatter(formatter)
logger.addHandler(logger_file_handler)

try:
    SOME_SECRET = os.environ["SOME_SECRET"]
except KeyError:
    SOME_SECRET = "Token not available!"
#logger.info("Token not available!")
#raise

def send_slack_message(webhook_url, message):
    payload = {"text": message}
    headers = {"Content-Type": "application/json"}

    response = requests.post(webhook_url, json=payload, headers=headers)

    if response.status_code == 200:
        print("Message sent successfully")
    else:
        print(f"Failed to send message: {response.status_code}, {response.text}")

def get_data(name):
    # Calculate the date range for the months
    end_date = datetime.today()
    start_date = end_date - timedelta(days=2000)
    df = yf.download(name, start=start_date, end=end_date, auto_adjust=True)[['High','Close','Low']]

    # Flatten MultiIndex columns if they exist
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Rename columns to lowercase for consistency
    df.columns = ['high', 'close', 'low']

    if 'Dividends' in df.columns:
        df = df.drop(columns=['Dividends'])

    # Get the 50-day EMA of the closing price
    ema_50 = df['close'].ewm(span=50, adjust=False, min_periods=50).mean()

    # Get the 200-day EMA of the closing price
    ema_200 = df['close'].ewm(span=200, adjust=False, min_periods=200).mean()

    # Add all of our new values for the MACD to the dataframe
    df['ema_50'] = ema_50
    df['ema_200'] = ema_200

    # View our data
    pd.set_option("display.max_columns", None)

    return df

def calculate_atr(df, period=15):
    """Calculate Average True Range (ATR) using pandas"""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    return atr

def supertrend(df, atr_multiplier=3):
    # Check if DataFrame is empty after downloading
    if df.empty:
        return df

    # Calculate the Upper Band(UB) and the Lower Band(LB)
    # Formula: Supertrend =(High+Low)/2 + (Multiplier)∗(ATR)
    current_average_high_low = (df['high']+df['low'])/2
    df['atr'] = calculate_atr(df, period=15)
    df.dropna(inplace=True)

    # Check again if DataFrame is empty after dropna
    if df.empty:
        return df

    df['basicUpperband'] = current_average_high_low + (atr_multiplier * df['atr'])
    df['basicLowerband'] = current_average_high_low - (atr_multiplier * df['atr'])
    first_upperBand_value = df['basicUpperband'].iloc[0]
    first_lowerBand_value = df['basicLowerband'].iloc[0]
    upperBand = [first_upperBand_value]
    lowerBand = [first_lowerBand_value]

    for i in range(1, len(df)):
        if df['basicUpperband'].iloc[i] < upperBand[i-1] or df['close'].iloc[i-1] > upperBand[i-1]:
            upperBand.append(df['basicUpperband'].iloc[i])
        else:
            upperBand.append(upperBand[i-1])

        if df['basicLowerband'].iloc[i] > lowerBand[i-1] or df['close'].iloc[i-1] < lowerBand[i-1]:
            lowerBand.append(df['basicLowerband'].iloc[i])
        else:
            lowerBand.append(lowerBand[i-1])

    df['upperband'] = upperBand
    df['lowerband'] = lowerBand
    df.drop(['basicUpperband', 'basicLowerband',], axis=1, inplace=True)
    return df

def generate_signals(df):
    # Check if DataFrame is empty
    if df.empty:
        return df

    # Intiate a signals list
    signals = [0]

    # Loop through the dataframe
    for i in range(1 , len(df)):
        if df['close'].iloc[i] > df['upperband'].iloc[i]:
            signals.append(1)
        elif df['close'].iloc[i] < df['lowerband'].iloc[i]:
            signals.append(-1)
        else:
            signals.append(signals[i-1])

    # Add the signals list as a new column in the dataframe
    df['signals'] = signals
    #df['signals'] = df["signals"].shift(1) #Remove look ahead bias
    return df

def trigger(df):
    if(df['signals'].iloc[-1]==1 and df['signals'].iloc[-2]==-1):
        if(df['ema_50'].iloc[-1]>df['ema_200'].iloc[-1] and df['close']>0.5):
            return True
        else:
            return False
    #elif(df['signals'].iloc[-1]==-1):
        #if(df['ema_50'].iloc[-1]<df['ema_200'].iloc[-1]):
            #return False
    else:
        return False




if __name__ == "__main__":
    logger.info(f"Token value: {SOME_SECRET}")

    start = timeit.default_timer()

    compName=pd.read_csv("stock_list.csv")


    coSymbol=compName["code"]
    coName=compName["name"] 
    message="Supertrend My Stocks: "

    coName_list=coName.tolist()
    coSymbol_list=coSymbol.tolist()

    

    i=0
    # Process all legitimate stocks from the clean CSV
    for i in range(len(coName.index)):
        company_name = coName_list[i]
        symbol = coSymbol_list[i] + ".KL"
            
        try:
            df=get_data(symbol)

            if(df.empty):
                print(f"\nSymbol= {symbol} ({company_name}) data not found")
                continue
        except Exception as e:
            print(f"\nError processing {symbol} ({company_name}): {str(e)}")
            continue

        supertrend_data = supertrend(df, atr_multiplier=3)

        if(supertrend_data.empty):
            print(f"\nSymbol= {symbol} ({company_name}) insufficient data for analysis")
            continue

        # Generate the Signals
        supertrend_positions = generate_signals(supertrend_data)

        if(supertrend_positions.empty):
            print(f"\nSymbol= {symbol} ({company_name}) insufficient data for signals")
            continue

        flag=trigger(supertrend_positions)
        if(flag is True):
            print(f"\nTrigger hit! Symbol= {symbol} ({company_name})")
            message=message + f" {company_name}"


            
        # Sleep for 1 second to be respectful to the API
        time.sleep(1)


    #Replace with your webhook URL
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]



    send_slack_message(webhook_url, message)


    #Your statements here

    stop = timeit.default_timer()
    print(message)
    print('Time: ', stop - start)
