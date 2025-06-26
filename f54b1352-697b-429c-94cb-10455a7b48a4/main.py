from surmount.base_class import Strategy, TargetAllocation
from surmount.logging import log
from surmount.technical_indicators import STDEV
from datetime import datetime, timedelta

class TradingStrategy(Strategy):
    def __init__(self):
        self.tickers = ["MSFT", "ARM", "NVDA", "AMD"]
        self.data_list = []
        self.min_days = 64
        self.last_allocation = None  # Store previous allocation
        self.last_rebalance_date = None  # Track last rebalance

    @property
    def assets(self):
        return self.tickers

    @property
    def interval(self):
        return "1day"

    @property
    def data(self):
        return self.data_list

    def is_quarter_end(self, date):
        """Check if the date is the last trading day of a quarter."""
        next_day = date + timedelta(days=1)
        current_quarter = (date.month - 1) // 3 + 1
        next_quarter = (next_day.month - 1) // 3 + 1
        return current_quarter != next_quarter  # True if crossing quarter boundary

    def run(self, data):
        ohlcv = data["ohlcv"]
        
        closes = [entry['MSFT']["close"] for entry in ohlcv]
        if len(closes) < 1:
            return TargetAllocation({ticker: 0.25 for ticker in self.tickers})

        current_date = datetime.strptime(ohlcv[-1][self.tickers[0]]["date"], "%Y-%m-%d %H:%M:%S")
        # Parse current date from latest OHLCV entry
        prices = {ticker: [d[ticker]["close"] for d in ohlcv if ticker in d] for ticker in self.tickers}
       

        # Use last allocation if available and not rebalancing
        if self.last_allocation and not self.is_quarter_end(current_date):
            #log("Not quarter-end, using previous allocation")
            return TargetAllocation(self.last_allocation)

        # Default to equal weights if insufficient data for full analysis
        allocation_dict = {ticker: 0.25 for ticker in self.tickers}
        if len(ohlcv) < 63:
            #log("Less than 63 days, using equal weights")
            self.last_allocation = allocation_dict
            self.last_rebalance_date = current_date
            return TargetAllocation(allocation_dict)

        # Quarterly rebalancing logic (only on quarter-end)
        if not self.is_quarter_end(current_date):
            #log("Not quarter-end, skipping rebalance")
            return TargetAllocation(self.last_allocation or allocation_dict)

        log("Quarter-end rebalancing triggered")
        quarterly_returns = {ticker: (prices[ticker][-1] / prices[ticker][-63]) - 1 
                            if len(prices[ticker]) >= 63 else 0 for ticker in self.tickers}

        # Calculate volatility over the last quarter
        volatilities = {}
        for ticker in self.tickers:
            vol = STDEV(ticker, ohlcv[-63:], 63)
            volatilities[ticker] = vol[-1] if vol and len(vol) > 0 else 0.1

        # Inverse volatility weighting
        inverse_vol_sum = sum(1 / max(v, 0.01) for v in volatilities.values())
        allocation_dict = {ticker: (1 / max(volatilities[ticker], 0.01)) / inverse_vol_sum 
                          for ticker in self.tickers}

        # Profit-Taking Rule: NVDA or ARM up 40% in a quarter
        for ticker in ["NVDA", "ARM"]:
            if quarterly_returns[ticker] >= 0.4:
                #log(f"{ticker} up 40%+, rebalancing to equal-weight")
                allocation_dict = {t: 0.25 for t in self.tickers}
                break

        # Stop-Loss Rule: AMD drops >15% in a month (21 days)
        if len(prices["AMD"]) >= 21:
            monthly_return = (prices["AMD"][-1] / prices["AMD"][-21]) - 1
            if monthly_return <= -0.15:
                #log("AMD dropped >15% in a month, reducing exposure by half")
                allocation_dict["AMD"] *= 0.5
                remaining = sum(allocation_dict[t] for t in self.tickers if t != "AMD")
                for t in self.tickers:
                    if t != "AMD":
                        allocation_dict[t] = allocation_dict[t] / remaining * (1 - allocation_dict["AMD"])

        # Volatility Spike Rule: MSFT volatility 50% above historical average
        msft_vol = volatilities["MSFT"]
        msft_hist_vol = STDEV("MSFT", ohlcv, len(ohlcv))
        msft_hist_vol = msft_hist_vol[-1] if msft_hist_vol and len(msft_hist_vol) > 0 else msft_vol
        if msft_vol > msft_hist_vol * 1.5:
            #log("MSFT volatility spiked 50% above average, rebalancing")
            allocation_dict = {t: 0.25 for t in self.tickers}

        # Normalize allocation to sum to 1
        total = sum(allocation_dict.values())
        if total > 0:
            allocation_dict = {t: w / total for t, w in allocation_dict.items()}

        # Store allocation and rebalance date
        self.last_allocation = allocation_dict
        self.last_rebalance_date = current_date
        return TargetAllocation(allocation_dict)