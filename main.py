import logging
import logging.handlers
import os

import requests
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import timeit

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


def get_ema(name):
    # Calculate the date range for the months
    end_date = datetime.today()
    start_date = end_date - timedelta(days=1000)
    df = yf.download(name, start=start_date, end=end_date)[['Close', 'Low']]

    if 'Dividends' in df.columns:
        df = df.drop(columns=['Dividends'])


    # Get the 12-day EMA of the closing price
    ema_12 = df['Close'].ewm(span=12, adjust=False, min_periods=12).mean()

    # Get the 144-day EMA of the closing price
    ema_144 = df['Close'].ewm(span=144, adjust=False, min_periods=144).mean()

    # Get the 169-day EMA of the closing price
    ema_169 = df['Close'].ewm(span=169, adjust=False, min_periods=169).mean()

    # Get the 576-day EMA of the closing price
    ema_576 = df['Close'].ewm(span=576, adjust=False, min_periods=576).mean()

    # Get the 676-day EMA of the closing price
    ema_676 = df['Close'].ewm(span=676, adjust=False, min_periods=676).mean()


    # Add all of our new values for the MACD to the dataframe
    df['ema_12'] = ema_12
    df['ema_144'] = ema_144
    df['ema_169']= ema_169
    df['ema_576'] = ema_576
    df['ema_676'] = ema_676

    # View our data
    pd.set_option("display.max_columns", None)

    return df

def trigger(df):
    trigger_flag=False
    df_today=df.iloc[-1]
    five_day_low=df.iloc[-6:-1]["Low"]
    ema_144_5day=df.iloc[-6:-1]["ema_144"]
    breakout=True

    ema_12_td=df.iloc[-1]["ema_12"]
    ema_144_td=df.iloc[-1]["ema_144"]
    ema_169_td=df.iloc[-1]["ema_169"]
    ema_576_td=df.iloc[-1]["ema_576"]
    ema_676_td=df.iloc[-1]["ema_676"]
    close_p = df.iloc[-1]['Close']
    low_p= df.iloc[-1]['Low']

    if((ema_144_td > ema_576_td).all() and (ema_12_td>ema_144_td).all()):
        for i in range(0,len(five_day_low)):
            if(float(five_day_low.iloc[i])<float(ema_144_5day.iloc[i])):
                breakout=False
                break

        if(breakout==True):
            if(float(low_p) < float(ema_144_td)):
                trigger_flag=True

    return trigger_flag


if __name__ == "__main__":
    logger.info(f"Token value: {SOME_SECRET}")

    r = requests.get('https://weather.talkpython.fm/api/weather/?city=Berlin&country=DE')
    if r.status_code == 200:
        data = r.json()
        temperature = data["forecast"]["temp"]
        logger.info(f'Weather in Berlin: {temperature}')


    start = timeit.default_timer()

    compName=pd.read_csv("C:\\Users\\User\\python project\\project 2_algotrading\\constituents.csv")


    coName=compName["Symbol"]
    coType=compName["GICS Sector"]
    message="Stocks: "

    coName_list=coName.tolist()
    coType_list=coType.tolist()

    i=0
    for i in range(len(coName.index)):
        df=get_ema(coName_list[i])
        if(df.empty):
            print("\nSymbol= "+coName_list[i]+" data not found")

        else:
            flag=trigger(df)
            if(flag==True):
                print("\nSymbol= "+coName_list[i])
                print("\nSector= "+coType_list[i])
                message=message + " " + coName_list[i]
        
                

    # Replace with your webhook URL
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]


    send_slack_message(webhook_url, message)


    #Your statements here

    stop = timeit.default_timer()
    print(message)
    print('Time: ', stop - start)