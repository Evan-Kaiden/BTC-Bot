import cbpro
import pandas as pd
import ta
import math
import time
import config

print("Program Starting")



API_KEY =  config.API_Key
API_SECRET = config.API_Secret
API_PASSPHRASE = config.passphrase


auth_client = cbpro.AuthenticatedClient(API_KEY, API_SECRET, API_PASSPHRASE)
public_client = cbpro.PublicClient()


product = 'BTC-USD'


rsi_period = 14 
time_period = 300 #chart time in seconds
order_book = []
stop = 0.98 
take = 1.04



def calc_live_rsi(price):

    candles = public_client.get_product_historic_rates(product, granularity=time_period)
    candles.reverse() #Get most recent candles
    closing_prices = [candle[4] for candle in candles]
    rsi_indicator = ta.momentum.RSIIndicator(close=pd.Series(closing_prices), window=rsi_period)

    # Calculate the RSI using the current price
    current_closing_prices = closing_prices + [price]
    current_rsi_indicator = ta.momentum.RSIIndicator(close=pd.Series(current_closing_prices), window=rsi_period)
    current_rsi = current_rsi_indicator.rsi().iloc[-1]

    return current_rsi

def calc_live_macd(price):
    # Fetch the historical candles data
    candles = public_client.get_product_historic_rates(product, granularity=time_period)
    candles.reverse()
    closing_prices = [candle[4] for candle in candles]

    # Calculate the MACD using the historical candles data
    macd_indicator = ta.trend.MACD(close=pd.Series(closing_prices), window_fast=12, window_slow=26, window_sign=9)
    macd = macd_indicator.macd().iloc[-1]
    signal = macd_indicator.macd_signal().iloc[-1]

    # Calculate the MACD using the current price
    current_closing_prices = closing_prices + [price]
    current_macd_indicator = ta.trend.MACD(close=pd.Series(current_closing_prices), window_fast=12, window_slow=26, window_sign=9)
    current_macd = current_macd_indicator.macd().iloc[-1]
    current_signal = current_macd_indicator.macd_signal().iloc[-1]

    return current_macd, current_signal

def buy_trigger(rsi, macd, signal):
    if (rsi < 30) & (signal > macd) & (signal < 0):
        return True
    return False

def sell_trigger(rsi, macd, signal, price, take, buy):
    if (rsi > 70) and (macd > signal):
        return True
    if buy * take <= price:
        return True
    return False

def check_seq():
    ticker = auth_client.get_product_ticker(product_id=product)
    price = ticker['price']
    price = float(price)
    return price

def stop_loss(buy, stop, price):
    if buy * stop >= price:
        return True

while True:
    try:
        price = check_seq()
        rsi = calc_live_rsi(price)
        macd, signal = calc_live_macd(price)

        if buy_trigger(rsi, macd, signal):
            usd_balance = (math.floor(float(auth_client.get_account('e182e353-a4a8-4554-9f39-078a54378e26')['balance']) * 100) / 100)
            msg = auth_client.place_market_order(product_id=product, side='buy', funds=usd_balance)
            print(msg)
            print("BUY at ", price, time.ctime())
            buy_price = price

            while True:
                    price = check_seq()
                    rsi = calc_live_rsi(price)
                    macd, signal = calc_live_macd(price)

                    if stop_loss(buy_price, stop, price):
                        bitcoin_balance = float(auth_client.get_account('9c7ef734-b8f4-46c7-9889-f81ee8c3dcd3')['balance'])
                        msg = auth_client.place_market_order(product_id=product, side='sell', size=bitcoin_balance)
                        print(msg)
                        print('STOP LOSS sell at ', price, time.ctime())
                        time.sleep(60)
                        break

                    if sell_trigger(rsi, macd, signal, price, take, buy_price):
                        bitcoin_balance = float(auth_client.get_account('9c7ef734-b8f4-46c7-9889-f81ee8c3dcd3')['balance'])
                        msg = auth_client.place_market_order(product_id=product, side='sell', size=bitcoin_balance)
                        print(msg)
                        print("SELL at", price, time.ctime())
                        break

                    time.sleep(3)
        time.sleep(3)
    except:
        time.sleep(3)