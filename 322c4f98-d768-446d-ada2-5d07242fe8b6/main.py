from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import RSI, SMA
from surmount.data import Ratios
from datetime import datetime, timedelta

class TradingStrategy(Strategy):

    def __init__(self):
        # Core tickers
        self.tickers = ["ICLN", "NEE", "FSLR", "PLUG", "ENPH", "ALB", "TSLA"]
        # Add P/B ratio as extra data source
        self.data_list = [Ratios(ticker) for ticker in self.tickers]

    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return self.tickers

    @property
    def data(self):
        return self.data_list

    def run(self, data):
        ohlcv = data["ohlcv"]
        pb_ratios = {ticker: None for ticker in self.tickers}
        close_prices = {ticker: [day[ticker]["close"] for day in ohlcv if ticker in day] for ticker in self.tickers}
        allocation = {}

        # Stop-loss: if below 200-day SMA, do not allocate
        below_200dma = {}
        for ticker in self.tickers:
            sma_200 = SMA(ticker, ohlcv, 200)
            if sma_200 and len(sma_200) > 0:
                below_200dma[ticker] = close_prices[ticker][-1] < sma_200[-1]
            else:
                below_200dma[ticker] = False

        

        # Get P/B ratios
        for d in self.data_list:
            if tuple(d)[0] == "ratios":
                ticker = tuple(d)[1]
                vals = data[tuple(d)]
                if vals and "priceToBook" in vals[-1]:
                    pb_ratios[ticker] = vals[-1]["priceToBook"]

        # Compute P/B median excluding ICLN
        pb_values = [pb_ratios[t] for t in self.tickers if t != "ICLN" and pb_ratios[t] is not None]
        pb_median = sorted(pb_values)[len(pb_values)//2] if pb_values else 1

        # Weighting factors
        weights = {}
        base_weight = 1.0  # initial full weight to be normalized later

        for ticker in self.tickers:
            if ticker not in allocation and not below_200dma[ticker]:
                # Mean reversion: PLUG or ENPH drop >20% in past quarter (~60 trading days)
                if ticker in ["PLUG", "ENPH"]:
                    price_now = close_prices[ticker][-1]
                    if len(close_prices[ticker]) > 60:
                        price_60 = close_prices[ticker][-61]
                        if price_now < price_60 * 0.8:
                            weights[ticker] = base_weight * 1.5  # overweight
                            continue

                # Sector trend: if ICLN rose 10%+ in past 21 days (~month), overweight renewables
                if ticker != "ICLN" and "ICLN" in close_prices and len(close_prices["ICLN"]) > 21:
                    icln_growth = close_prices["ICLN"][-1] / close_prices["ICLN"][-22]
                    if icln_growth >= 1.1:
                        weights[ticker] = base_weight * 1.25
                        continue

                # P/B undervaluation (excluding ICLN)
                if ticker != "ICLN" and pb_ratios[ticker] is not None and pb_ratios[ticker] < pb_median:
                    weights[ticker] = base_weight * 1.25
                else:
                    weights[ticker] = base_weight

        # RSI-based sell signal for TSLA
        tsla_rsi = RSI("TSLA", ohlcv, 14)
        if tsla_rsi and tsla_rsi[-1] > 85:
            allocation["TSLA"] = 0  # Take profit
        elif tsla_rsi and tsla_rsi[-1] < 30:
            allocation["TSLA"] = 1  # Buy

        # Normalize to [0,1]
        total = sum(weights.values())
        for t in weights:
            allocation[t] = weights[t] / total if total > 0 else 0

        return TargetAllocation(allocation)