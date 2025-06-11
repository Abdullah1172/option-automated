#   HV-7 CONDOR  |  QuantConnect Lean (Python)  |  SPY 7-DTE IV-filtered iron-condor engine
#
#   ✔ 20-δ shorts, $5 wings            ✔ Mon/Wed 15:40 ET entry
#   ✔ VIX > 18  &  1-year IV-rank ≥40  ✔ Profit-target = 50 % credit
#   ✔ Max-loss = 1.5× credit           ✔ Roll/stop if short-strike Δ > 0.30
#   ✔ Portfolio risk cap = 35 %        ✔ Auto-close ≥2 days before expiry
#
#   Drop this single file into a QuantConnect project and hit Backtest.
#
from AlgorithmImports import *
import numpy as np

class HV7Condor(QCAlgorithm):

    # -------- CONFIG --------------------------------------------------------
    UNDERLYING      = "SPY"
    RISK_CAP        = 0.35            # ≤ 35 % portfolio at risk
    DTE_MIN, DTE_MAX = 6, 8           # 7-DTE window
    SHORT_DELTA     = 0.20            # target abs(Δ) for short legs
    WING_WIDTH      = 5               # $5-wide wings
    VIX_MIN         = 18.0            # VIX filter
    IVR_MIN         = 0.40            # 40 % IV-rank filter
    CREDIT_TARGET   = 0.30            # want ≥30 % of width
    PROFIT_TGT_PCT  = 0.50            # 50 % profit-take
    LOSS_STOP_MULT  = 1.50            # 1.5× credit stop
    DELTA_ROLL_TRIG = 0.30            # roll if |Δshort| > 0.30
    MANAGE_HOUR     = 15              # daily management time
    MANAGE_MINUTE   = 50

    # -----------------------------------------------------------------------
    def Initialize(self):
        self.SetStartDate(2023, 12, 1)   # Changed to Dec 2023
        self.SetEndDate(2024, 12, 1)     # Added end date Dec 2024
        self.SetCash(100_000)
        self.SetTimeZone("America/New_York")
        self.Settings.EnableGreekApproximation = True

        # Underlying & option chain
        self.spy = self.AddEquity(self.UNDERLYING, Resolution.Minute).Symbol
        opt = self.AddOption(self.UNDERLYING, Resolution.Minute)
        opt.SetFilter(self.UniverseFunc)
        self.opt_symbol = opt.Symbol

        # VIX index (for filter & IV-rank proxy)
        self.vix = self.AddData(CBOE, "VIX", Resolution.Daily).Symbol
        self.SetWarmup(timedelta(days=252))  # need 1-yr history for IV-rank proxy

        # Containers
        self.condors = {}     # key: ticket-id → dict(details)
        self.next_trade_day = None

        # Schedule entry (Mon & Wed 15:40 ET) and daily management
        self.Schedule.On(
            self.DateRules.Every(DayOfWeek.Monday, DayOfWeek.Wednesday),
            self.TimeRules.At(15, 40),
            self.OpenCondor
        )
        self.Schedule.On(
            self.DateRules.EveryDay(),
            self.TimeRules.At(self.MANAGE_HOUR, self.MANAGE_MINUTE),
            self.ManagePositions
        )

    # -------- OPTION UNIVERSE FILTER ---------------------------------------
    def UniverseFunc(self, universe: OptionFilterUniverse):
        return (universe
                .WeeklysOnly()
                .Strikes(-30, 30)
                .Expiration(self.DTE_MIN, self.DTE_MAX))

    # -------- ENTRY --------------------------------------------------------
    def OpenCondor(self):
        # --- 1) VOLATILITY FILTERS
        vix_current = self.Securities[self.vix].Price
        if vix_current < self.VIX_MIN:
            self.Log(f"SKIP - VIX {vix_current:.1f} < {self.VIX_MIN}")
            return
        iv_rank = self.GetIVRank()
        if iv_rank is None or iv_rank < self.IVR_MIN:
            self.Log(f"SKIP - IV-Rank {iv_rank:.2f} < {self.IVR_MIN}")
            return

        # --- 2) RISK BUDGET
        risk_budget = self.Portfolio.TotalPortfolioValue * self.RISK_CAP
        risk_in_use = sum(cd["risk"] for cd in self.condors.values())
        room = risk_budget - risk_in_use
        if room < self.WING_WIDTH * 100:
            self.Log("SKIP - Risk cap reached")
            return

        # --- 3) CHAIN SELECTION
        chain = self.CurrentSlice.OptionChains.get(self.opt_symbol)
        if not chain:
            self.Log("No chain yet")
            return

        # pick nearest expiry in window
        expiry = sorted(chain, key=lambda x: x.Expiry)[0].Expiry
        chain = [c for c in chain if c.Expiry == expiry]

        # greeks may not yet be populated immediately after warm-up
        candidates = [c for c in chain if c.Greeks.Delta is not None]

        short_put  = min((c for c in candidates if c.Right==OptionRight.Put),
                         key=lambda c: abs(c.Greeks.Delta + self.SHORT_DELTA),
                         default=None)
        short_call = min((c for c in candidates if c.Right==OptionRight.Call),
                         key=lambda c: abs(c.Greeks.Delta - self.SHORT_DELTA),
                         default=None)
        if not (short_put and short_call):
            self.Log("SKIP - could not find 20-δ shorts")
            return

        # wings
        wing_put  = self.GetContract(candidates, short_put.Strike  - self.WING_WIDTH,  OptionRight.Put, expiry)
        wing_call = self.GetContract(candidates, short_call.Strike + self.WING_WIDTH, OptionRight.Call, expiry)
        if not (wing_put and wing_call):
            self.Log("SKIP - missing wing strikes")
            return

        # --- 4) CREDIT & POSITION SIZE
        condor = OptionStrategyFactory.CreateIronCondor(self.opt_symbol,
                                                        short_put.Strike,  wing_put.Strike,
                                                        short_call.Strike, wing_call.Strike,
                                                        expiry)
        quote = self.OptionStrategyPrice(condor)
        if quote is None:
            self.Log("Quote unavailable")
            return
        credit = quote.AskPrice   # we SELL the condor; use ask (worst case)
        if credit < self.WING_WIDTH * self.CREDIT_TARGET:
            self.Log(f"SKIP - Credit {credit:.2f} < target {self.WING_WIDTH*self.CREDIT_TARGET:.2f}")
            return

        risk_per_condor = (self.WING_WIDTH-credit) * 100   # max loss per 1-lot
        qty = int(room // risk_per_condor)
        if qty == 0: qty = 1
        order = self.Sell(condor, qty)
        if order.Status != OrderStatus.Submitted:
            self.Log("Order not submitted")
            return

        # store
        self.condors[order.Id] = {
            "strategy": condor,
            "qty": qty,
            "credit": credit,
            "risk": risk_per_condor*qty,
            "expiry": expiry,
            "short_put": short_put.Symbol,
            "short_call": short_call.Symbol
        }
        self.Log(f"OPEN  condor {order.Id}: credit {credit:.2f} ×{qty}  IVR={iv_rank:.2f}")

    # -------- DAILY MANAGEMENT ---------------------------------------------
    def ManagePositions(self):
        close_ids = []
        open_ids  = list(self.condors.keys())

        for oid in open_ids:
            cd = self.condors[oid]
            strat_price = self.OptionStrategyPrice(cd["strategy"])
            if strat_price is None:
                continue

            # profit-take
            if strat_price <= cd["credit"] * self.PROFIT_TGT_PCT:
                self.Buy(cd["strategy"], cd["qty"])
                close_ids.append(oid)
                self.Log(f"TP   condor {oid}  closed at {strat_price:.2f}")
                continue

            # stop-loss
            if strat_price >= cd["credit"] * self.LOSS_STOP_MULT:
                self.Buy(cd["strategy"], cd["qty"])
                close_ids.append(oid)
                self.Log(f"SL   condor {oid}  closed at {strat_price:.2f}")
                continue

            # time exit (≥2 days to expiry)
            if (cd["expiry"] - self.Time).days <= 2:
                self.Buy(cd["strategy"], cd["qty"])
                close_ids.append(oid)
                self.Log(f"T-exit condor {oid}")
                continue

            # delta-based roll
            sp = self.Securities[cd["short_put"]]
            sc = self.Securities[cd["short_call"]]
            if (abs(sp.Greeks.Delta) > self.DELTA_ROLL_TRIG or
                abs(sc.Greeks.Delta) > self.DELTA_ROLL_TRIG):
                self.Buy(cd["strategy"], cd["qty"])
                close_ids.append(oid)
                self.Log(f"ROLL condor {oid}  (Δ hit); will open new condor next entry window")

        # cleanup dictionary
        for oid in close_ids:
            self.condors.pop(oid, None)

    # -------- HELPERS -------------------------------------------------------
    def GetIVRank(self):
        """1-year IV-rank proxy using VIX high/low."""
        hist = self.History(self.vix, 252, Resolution.Daily)
        if hist.empty: return None
        vMin, vMax = hist["close"].min(), hist["close"].max()
        vNow = self.Securities[self.vix].Price
        return (vNow - vMin) / (vMax - vMin) if vMax > vMin else None

    def GetContract(self, chain, strike, right, expiry):
        """Return contract matching strike/right/expiry, else None."""
        for c in chain:
            if (abs(c.Strike - strike) < 1e-6 and
                c.Right == right and
                c.Expiry == expiry):
                return c
        return None

    def OptionStrategyPrice(self, strategy):
        """Return Bid/Ask mark for entire option strategy (average of legs)."""
        legs = [ (leg, qty) for leg, qty in strategy.OptionLegs ]
        prices = []
        for leg, qty in legs:
            sec = self.Securities[leg.Symbol]
            if not sec.HasData: return None
            price = sec.AskPrice if qty < 0 else sec.BidPrice   # we sold strategy
            prices.append(abs(qty) * price)
        if not prices: return None
        return sum(prices) / sum(abs(q) for _, q in legs)