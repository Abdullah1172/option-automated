# Iron Condor strategy for SPY
# Minute resolution, 6-month back-test

from AlgorithmImports import *
from datetime import timedelta


class IronCondorAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 1, 2)
        self.SetEndDate(2023, 7, 1)
        self.SetCash(100000)

        self.underlying = self.AddEquity("SPY", Resolution.Minute).Symbol
        option = self.AddOption("SPY", Resolution.Minute)
        option.SetFilter(-10, +10, timedelta(20), timedelta(40))

        self.SetWarmUp(timedelta(days=1))

    def OnData(self, slice: Slice):
        if self.IsWarmingUp or self.Portfolio.Invested:
            return

        chain = slice.OptionChains.get("SPY")
        if not chain:
            return

        # choose nearest expiry >20 days
        chain = sorted(chain, key=lambda c: c.Expiry)
        expiry = chain[0].Expiry
        contracts = [c for c in chain if c.Expiry == expiry]
        strikes = {c.Strike: c for c in contracts}

        price = self.Securities[self.underlying].Price
        atm = round(price / 5.0) * 5

        call_short = strikes.get(atm + 5)
        call_long = strikes.get(atm + 10)
        put_short = strikes.get(atm - 5)
        put_long = strikes.get(atm - 10)
        if None in (call_short, call_long, put_short, put_long):
            return

        condor = OptionStrategies.IronCondor(
            call_short.Symbol,
            call_long.Symbol,
            put_short.Symbol,
            put_long.Symbol,
            1,
        )
        self.Buy(condor, 1)
