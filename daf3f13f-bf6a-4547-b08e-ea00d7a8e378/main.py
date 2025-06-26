from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA
from surmount.logging import log

class TradingStrategy(Strategy):
    def __init__(self):
        self.tickers = ["TSM", "BABA", "TCEHY", "SE", "MELI", "AMX", "PBR"]

    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return self.tickers

    def run(self, data):
        ohlcv = data["ohlcv"]
        allocation = {ticker: 0 for ticker in self.tickers}
        total_weight = 0
        max_price = {ticker: max([candle[ticker]['close'] for candle in ohlcv]) for ticker in self.tickers}

        for ticker in self.tickers:
            if len(ohlcv) < 200:
                continue  # Ensure sufficient data

            sma_50 = SMA(ticker, ohlcv, 50)
            sma_200 = SMA(ticker, ohlcv, 200)

            if not sma_50 or not sma_200:
                continue

            current_price = ohlcv[-1][ticker]['close']
            
            # Determine overweight or underweight based on SMA
            if current_price > sma_50[-1] and current_price > sma_200[-1]:
                weight = 0.2  # Overweight allocation
            else:
                weight = 0.1  # Underweight allocation

            # Profit-taking rule
            if len(ohlcv) >= 60:  # Ensure 3 months of data
                past_price = ohlcv[-60][ticker]['close']
                if current_price >= 1.5 * past_price:
                    #log(f"Profit-taking: Trimming {ticker}")
                    #weight *= 0.5
                    weight = 0.1

            # Stop-loss rule
            if current_price <= 0.8 * max_price[ticker]:
                #log(f"Stop-loss: Trimming {ticker}")
                weight = 0.1

            allocation[ticker] = weight
            total_weight += weight

        # Normalize allocations to sum <= 1
        if total_weight > 1:
            excess = (total_weight - 1) / len(self.tickers)
            #allocation = {k: v / total_weight for k, v in allocation.items()}
            allocation = {k: v - excess for k, v in allocation.items()}

        return TargetAllocation(allocation)