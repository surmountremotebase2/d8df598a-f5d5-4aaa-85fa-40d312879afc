from surmount.base_class import Strategy, TargetAllocation
from surmount.technical_indicators import SMA, STDEV
from surmount.logging import log

class TradingStrategy(Strategy):
    def __init__(self):
        self.tickers = ["MRNA", "BNTX", "ISRG", "TDOC", "VRTX", "UNH"]

    @property
    def interval(self):
        return "1day"

    @property
    def assets(self):
        return self.tickers

    def run(self, data):
        ohlcv = data["ohlcv"]
        allocation = {ticker: 0 for ticker in self.tickers}
        momentum_scores = {}
        
        for ticker in self.tickers:
            if len(ohlcv) < 126:
                continue  # Ensure we have at least 6 months of data

            close_prices = [day[ticker]["close"] for day in ohlcv[-126:]]
            returns = (close_prices[-1] / close_prices[0]) - 1
            volatility = STDEV(ticker, ohlcv, 126)[-1] if STDEV(ticker, ohlcv, 126) else 1
            
            momentum_scores[ticker] = returns / volatility
        
        if not momentum_scores:
            return TargetAllocation(allocation)
        
        # Normalize momentum scores to allocate weight
        total_score = sum(max(score, 0) for score in momentum_scores.values())
        if total_score > 0:
            for ticker, score in momentum_scores.items():
                allocation[ticker] = max(score, 0) / total_score

        # Profit-Taking Rule: If MRNA or BNTX rises >30% in a month, sell 20%
        for ticker in ["MRNA", "BNTX"]:
            if ticker in ohlcv and len(ohlcv) >= 21:
                month_start_price = ohlcv[-21][ticker]["close"]
                month_end_price = ohlcv[-1][ticker]["close"]
                if month_end_price / month_start_price - 1 > 0.3:
                    allocation[ticker] *= 0.8  # Reduce position by 20%

        # Stop-Loss Rule: Remove stock if it drops >18% from its recent high
        for ticker in self.tickers:
            recent_high = max([day[ticker]["high"] for day in ohlcv[-30:]])
            if ohlcv[-1][ticker]["close"] < recent_high * 0.82:
                allocation[ticker] = 0  # Remove stock from portfolio

        # Defensive Rotation: Shift towards UNH when biotech underperforms
        biotech_tickers = ["MRNA", "BNTX", "ISRG", "TDOC", "VRTX"]
        biotech_momentum = sum(momentum_scores.get(ticker, 0) for ticker in biotech_tickers)
        unh_momentum = momentum_scores.get("UNH", 0)

        if biotech_momentum < unh_momentum:
            total_allocation = sum(allocation.values())
            if total_allocation > 0:
                for ticker in biotech_tickers:
                    allocation[ticker] *= 0.5  # Reduce biotech exposure
                allocation["UNH"] += 0.5  # Increase defensive positioning

        return TargetAllocation(allocation)