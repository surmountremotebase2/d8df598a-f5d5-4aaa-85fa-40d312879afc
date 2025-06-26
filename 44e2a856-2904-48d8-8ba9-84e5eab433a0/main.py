from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA
from surmount.logging import log


class TradingStrategy(Strategy):
    def __init__(self):
        self.tickers = ["SMR", "BWXT", "LEU", "CEG", "VST", "OKLO", "CCJ", "URA"]
        self.tradtick = ["SMR", "BWXT", "LEU", "CEG", "VST", "OKLO", "CCJ"]

    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return self.tickers

    @property
    def data(self):
        return []

    def run(self, data):
        ohlcv = data["ohlcv"]
        allocations = {}
        weights = {ticker: 1 for ticker in self.tradtick}
        index = [x["URA"]["close"] for x in ohlcv if "URA" in x]
        if len(index) > 1:
            incurrent = index[-1]
            inmonth_ago = index[-21]
            inmonth_return = (incurrent - inmonth_ago) / inmonth_ago

        # Edge case: Not enough data
        '''if len(index) < 1:
            log("Insufficient data. Using equal weights.")
            equal_weight = 1.0 / len(self.tickers)
            return TargetAllocation({ticker: equal_weight for ticker in self.tickers})'''

        # Compute 1-month and 3-month performance for all stocks
        for ticker in self.tradtick:
            prices = [x[ticker]["close"] for x in ohlcv if ticker in x]

            if len(prices) < 1:
                continue


            current = prices[-1]
            month_ago = prices[-21]
            quarter_ago = prices[-63]
            peak = max(prices[-63:])

            # Monthly performance
            month_return = (current - month_ago) / month_ago
            # Quarterly performance
            quarter_return = (current - quarter_ago) / quarter_ago
            # Peak drawdown from last 3 months
            drawdown = (current - peak) / peak

            # Adaptive overweighting based on CCJ price
            if ticker == "CCJ" and inmonth_return > 0.10:
                weights["CCJ"] += 2
                weights["LEU"] += 1

            # Profit-taking rule: Reduce allocation if up >40% in a quarter
            if quarter_return > 0.4:
                weights[ticker] *= 0.5

            # Stop-loss: reduce if down >18% from peak
            if drawdown < -0.18:
                weights[ticker] *= 0.5

        # Normalize weights to sum <= 1
        total_weight = sum(weights.values())
        if total_weight > 0:
            allocations = {ticker: weights[ticker] / total_weight for ticker in self.tradtick}
        else:
            allocations = {ticker: 1.0 / len(self.tradtick) for ticker in self.tradtick}

        return TargetAllocation(allocations)