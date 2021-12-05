import ccxt
import config
import schedule
import pandas as pd
import ta
pd.set_option('display.max_rows', None)

import warnings
warnings.filterwarnings('ignore')

import numpy as np
from datetime import datetime
import time

exchange = ccxt.binance({ 
    "apiKey" : config.BINANCE_API_KEY,
    "secret" : config.BINANCE_SECRET_KEY
})

def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])
    
    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)
    
    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()
    
    return atr

def supertrend(df, period=10, atr_multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df,period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True
    
    df['ema_200'] = ta.trend.EMAIndicator(df.close, window=200).ema_indicator()
   

    if(df.ema_200.iloc[-1] < df.close.iloc[-1]):        
        if df['close'][-1] > df['upperband'][-2]:
            df['in_uptrend'][-1] = True
        elif df['close'][-1] < df['lowerband'][-2]:
            df['in_uptrend'][-1] = False
        else:
            df['in_uptrend'][-1] = df['in_uptrend'][-2]
            
            if df['in_uptrend'][-1] and df['lowerband'][-1] < df['lowerband'][-2]:
                df['lowerband'][-1] = df['lowerband'][-2]
                
            if not df['in_uptrend'][-1] and df['upperband'][-1] > df['upperband'][-2]:
                df['upperband'][-1] = df['upperband'][-2]
                
    return df


in_position = False

def check_buy_sell_signals(df):
    global in_position
    
    print("checking for buy and sell signals")
    print(df[['timestamp','in_uptrend']].iloc[-1])
    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1
    
    if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
        print("changed to uptrend, buy")
        if not in_position:
            order = exchange.create_market_buy_order('BTC/USDT', 0.0045)
            print(order)
            in_position = True
        else:
            print("already in position, nothing to do")
        
    if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        if in_position:
            print("changed to downtrend, sell")
            order = exchange.create_market_sell_order('BTC/USDT', 0.0045)
            print(order)
            in_position = False
        else:
            print("you aren't in position, nothing to sell")


def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', limit=500)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    emasupertrend_data = supertrend(df)
    
    check_buy_sell_signals(emasupertrend_data)
    

schedule.every(10).seconds.do(run_bot)

while True:
    schedule.run_pending()
    time.sleep(1)
