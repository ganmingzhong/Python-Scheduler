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

def get_data(name):
    # Calculate the date range for the months
    end_date = datetime.today()
    start_date = end_date - timedelta(days=1000)
    df = yf.download(name, start=start_date, end=end_date)[['Close', 'Low']]

    if 'Dividends' in df.columns:
        df = df.drop(columns=['Dividends'])
    # View our data
    pd.set_option("display.max_columns", None)

    return df

def supertrend(df, atr_multiplier=3):
    # Calculate the Upper Band(UB) and the Lower Band(LB)
    # Formular: Supertrend =(High+Low)/2 + (Multiplier)∗(ATR)
    current_average_high_low = (df['high']+df['low'])/2
    df['atr'] = ta.atr(df['high'], df['low'], df['close'], period=15)
    df.dropna(inplace=True)
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


if __name__ == "__main__":
    logger.info(f"Token value: {SOME_SECRET}")

    start = timeit.default_timer()

    compName=pd.read_csv("C:\\Users\\User\\python project\\project 2_algotrading\\constituents.csv")


    coName=compName["Symbol"]
    coType=compName["GICS Sector"]
    message="Stocks: "

    coName_list=coName.tolist()
    coType_list=coType.tolist()

    i=0
    for i in range(len(coName.index)):
        df=get_data(coName_list[i])
        if(df.empty):
            print("\nSymbol= "+coName_list[i]+" data not found")

        else:
            flag=trigger(df)
            if(flag==True):
                print("\nSymbol= "+coName_list[i])
                print("\nSector= "+coType_list[i])
                message=message + " " + coName_list[i]
        break

    #Replace with your webhook URL
    webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    #webhook_url='https://hooks.slack.com/services/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'


    send_slack_message(webhook_url, message)


    #Your statements here

    stop = timeit.default_timer()
    print(message)
    print('Time: ', stop - start)
