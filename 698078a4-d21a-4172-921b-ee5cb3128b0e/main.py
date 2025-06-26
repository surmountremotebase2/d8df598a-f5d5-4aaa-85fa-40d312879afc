from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA, VWAP
from surmount.logging import log

class TradingStrategy(Strategy):
    def __init__(self):
        self.tickers = ["COIN", "NVDA", "MSTR", "AMD", "BITO"]
        self.btc_ticker = "BTC-USD"
        self.data_list = []
        self.weights = {"COIN": 0.1, "MSTR": 0.1, "NVDA": 0.1, "AMD": 0.1, "BITO": 0.1}

    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return self.tickers + [self.btc_ticker]

    @property
    def data(self):
        return self.data_list

    def run(self, data):
        ohlcv = data["ohlcv"]
        allocation = {ticker: 0 for ticker in self.tickers}
        
        if len(ohlcv) < 200:
            log("Not enough data for analysis")
            return TargetAllocation(allocation)
        
        btc_prices = [entry[self.btc_ticker]["close"] for entry in ohlcv]
        btc_50_ma = VWAP(self.btc_ticker, ohlcv, 50)[-1]
        btc_200_ma = VWAP(self.btc_ticker, ohlcv, 200)[-1]
        
        is_btc_bull = btc_prices[-1] > btc_200_ma
        is_btc_bear = btc_prices[-1] < btc_50_ma
        
        
        
        if is_btc_bull:  #set filter by stock 200ma
            self.weights["COIN"] = 0.2
            self.weights["MSTR"] = 0.2
            self.weights["BITO"] = 0.2
            self.weights["NVDA"] = 0.2
            #self.weights["AMD"] = 0.2
            #self.weights["BIL"] = 0.0
        elif is_btc_bear:
            self.weights["COIN"] = 0.0
            self.weights["BITO"] = 0.0
            self.weights["MSTR"] = 0.0
            self.weights["NVDA"] = 0.2
            #self.weights["BITO"] = 0.1
            #self.weights["BIL"] = 0.1
        
        for ticker in self.tickers:
            ticker_prices = [entry[ticker]["close"] for entry in ohlcv]
            peak_price = max(ticker_prices)
            drawdown = (peak_price - ticker_prices[-1]) / peak_price
            monthly_return = (ticker_prices[-1] / ticker_prices[-21]) - 1 if len(ticker_prices) > 21 else 0
            
            #if drawdown > 0.25:
            if drawdown > 0.05 and self.weights[ticker] > 0:
                #log(f"Stop-loss triggered for {ticker}, reducing exposure")
                self.weights[ticker] = 0.0
                #log(f"Drawdown {self.weights[ticker]}")
            
            if monthly_return > 0.50 and self.weights[ticker] > 0.05:
                #log(f"Profit-taking triggered for {ticker}, reducing exposure")
                self.weights[ticker] -= 0.05
                #log(f"Trimming {self.weights[ticker]}")
        
        total_weight = sum(self.weights.values())
        if total_weight > 0:
            allocation = {ticker: max(0, weight / total_weight) for ticker, weight in self.weights.items()}
        #log(f"{allocation}")
        
        return TargetAllocation(allocation)