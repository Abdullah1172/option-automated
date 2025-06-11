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

class IronCondorTest(QCAlgorithm):

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
    def initialize(self):
        self.set_start_date(2023, 12, 1)   # Changed to Dec 2023
        self.set_end_date(2024, 12, 1)     # Added end date Dec 2024
        self.set_cash(100_000)
        self.set_time_zone("America/New_York")

        # Underlying & option chain
        self.spy = self.add_equity(self.UNDERLYING, Resolution.MINUTE).symbol
        opt = self.add_option(self.UNDERLYING, Resolution.MINUTE)
        opt.set_filter(self.universe_func)
        self.opt_symbol = opt.symbol

        # VIX index (for filter & IV-rank proxy)
        self.vix = self.add_data(CBOE, "VIX", Resolution.DAILY).symbol
        self.set_warm_up(timedelta(days=252))  # need 1-yr history for IV-rank proxy

        # Containers
        self.condors = {}     # key: condor-id → dict(details)
        self.next_trade_day = None

        # Schedule entry (Mon & Wed 15:40 ET) and daily management
        self.schedule.on(
            self.date_rules.every(DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY),
            self.time_rules.at(15, 40),
            self.open_condor
        )
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.at(self.MANAGE_HOUR, self.MANAGE_MINUTE),
            self.manage_positions
        )

    # -------- OPTION UNIVERSE FILTER ---------------------------------------
    def universe_func(self, universe):
        return (universe
                .weeklys_only()
                .strikes(-30, 30)
                .expiration(self.DTE_MIN, self.DTE_MAX))

    # -------- ENTRY --------------------------------------------------------
    def open_condor(self):
        # --- 1) VOLATILITY FILTERS
        vix_current = self.securities[self.vix].price
        if vix_current < self.VIX_MIN:
            self.log(f"SKIP - VIX {vix_current:.1f} < {self.VIX_MIN}")
            return
        iv_rank = self.get_iv_rank()
        if iv_rank is None or iv_rank < self.IVR_MIN:
            self.log(f"SKIP - IV-Rank {iv_rank:.2f} < {self.IVR_MIN}")
            return

        # --- 2) RISK BUDGET
        risk_budget = self.portfolio.total_portfolio_value * self.RISK_CAP
        risk_in_use = sum(cd["risk"] for cd in self.condors.values())
        room = risk_budget - risk_in_use
        if room < self.WING_WIDTH * 100:
            self.log("SKIP - Risk cap reached")
            return

        # --- 3) CHAIN SELECTION
        chain = self.current_slice.option_chains.get(self.opt_symbol)
        if not chain:
            self.log("No chain yet")
            return

        # pick nearest expiry in window
        expiry = sorted(chain, key=lambda x: x.expiry)[0].expiry
        chain_list = [c for c in chain if c.expiry == expiry]

        # greeks may not yet be populated immediately after warm-up
        candidates = [c for c in chain_list if c.greeks.delta is not None]

        short_put  = min((c for c in candidates if c.right==OptionRight.PUT),
                         key=lambda c: abs(c.greeks.delta + self.SHORT_DELTA),
                         default=None)
        short_call = min((c for c in candidates if c.right==OptionRight.CALL),
                         key=lambda c: abs(c.greeks.delta - self.SHORT_DELTA),
                         default=None)
        if not (short_put and short_call):
            self.log("SKIP - could not find 20-δ shorts")
            return

        # wings
        wing_put  = self.get_contract(candidates, short_put.strike  - self.WING_WIDTH,  OptionRight.PUT, expiry)
        wing_call = self.get_contract(candidates, short_call.strike + self.WING_WIDTH, OptionRight.CALL, expiry)
        if not (wing_put and wing_call):
            self.log("SKIP - missing wing strikes")
            return

        # --- 4) CREDIT & POSITION SIZE
        # Calculate expected credit for iron condor
        wing_put_price = wing_put.ask_price if wing_put.ask_price > 0 else 0.01
        short_put_price = short_put.bid_price if short_put.bid_price > 0 else 0.01
        short_call_price = short_call.bid_price if short_call.bid_price > 0 else 0.01
        wing_call_price = wing_call.ask_price if wing_call.ask_price > 0 else 0.01
        
        # Net credit = sell puts + sell calls - buy wings
        credit = short_put_price + short_call_price - wing_put_price - wing_call_price
        
        if credit < self.WING_WIDTH * self.CREDIT_TARGET:
            self.log(f"SKIP - Credit {credit:.2f} < target {self.WING_WIDTH*self.CREDIT_TARGET:.2f}")
            return

        risk_per_condor = (self.WING_WIDTH - credit) * 100   # max loss per 1-lot
        qty = int(room // risk_per_condor)
        if qty == 0: qty = 1

        # Execute iron condor as individual orders
        condor_id = f"IC_{int(self.time.timestamp())}"
        
        # Buy protective put wing (long)
        order1 = self.market_order(wing_put.symbol, -qty)
        # Sell short put (short)  
        order2 = self.market_order(short_put.symbol, qty)
        # Sell short call (short)
        order3 = self.market_order(short_call.symbol, qty) 
        # Buy protective call wing (long)
        order4 = self.market_order(wing_call.symbol, -qty)

        # store condor details
        self.condors[condor_id] = {
            "qty": qty,
            "credit": credit,
            "risk": risk_per_condor * qty,
            "expiry": expiry,
            "wing_put": wing_put.symbol,
            "short_put": short_put.symbol,
            "short_call": short_call.symbol,
            "wing_call": wing_call.symbol,
            "orders": [order1.order_id, order2.order_id, order3.order_id, order4.order_id]
        }
        self.log(f"OPEN  condor {condor_id}: credit {credit:.2f} ×{qty}  IVR={iv_rank:.2f}")

    # -------- DAILY MANAGEMENT ---------------------------------------------
    def manage_positions(self):
        close_ids = []
        
        for condor_id, cd in self.condors.items():
            # Calculate current strategy value
            current_value = self.get_condor_value(cd)
            if current_value is None:
                continue

            # profit-take
            if current_value <= cd["credit"] * self.PROFIT_TGT_PCT:
                self.close_condor(cd)
                close_ids.append(condor_id)
                self.log(f"TP   condor {condor_id}  closed at {current_value:.2f}")
                continue

            # stop-loss
            if current_value >= cd["credit"] * self.LOSS_STOP_MULT:
                self.close_condor(cd)
                close_ids.append(condor_id)
                self.log(f"SL   condor {condor_id}  closed at {current_value:.2f}")
                continue

            # time exit (≥2 days to expiry)
            if (cd["expiry"] - self.time).days <= 2:
                self.close_condor(cd)
                close_ids.append(condor_id)
                self.log(f"T-exit condor {condor_id}")
                continue

            # delta-based roll
            sp = self.securities[cd["short_put"]]
            sc = self.securities[cd["short_call"]]
            if (hasattr(sp, 'greeks') and sp.greeks and abs(sp.greeks.delta) > self.DELTA_ROLL_TRIG) or \
               (hasattr(sc, 'greeks') and sc.greeks and abs(sc.greeks.delta) > self.DELTA_ROLL_TRIG):
                self.close_condor(cd)
                close_ids.append(condor_id)
                self.log(f"ROLL condor {condor_id}  (Δ hit); will open new condor next entry window")

        # cleanup dictionary
        for condor_id in close_ids:
            self.condors.pop(condor_id, None)

    def close_condor(self, condor_details):
        """Close iron condor by reversing all positions"""
        qty = condor_details["qty"]
        # Reverse all positions
        self.market_order(condor_details["wing_put"], qty)      # sell the long put
        self.market_order(condor_details["short_put"], -qty)    # buy back short put
        self.market_order(condor_details["short_call"], -qty)   # buy back short call
        self.market_order(condor_details["wing_call"], qty)     # sell the long call

    def get_condor_value(self, condor_details):
        """Calculate current value of iron condor"""
        try:
            wp = self.securities[condor_details["wing_put"]]
            sp = self.securities[condor_details["short_put"]]
            sc = self.securities[condor_details["short_call"]]
            wc = self.securities[condor_details["wing_call"]]
            
            if not all([wp.has_data, sp.has_data, sc.has_data, wc.has_data]):
                return None
                
            # Current cost to close the position (we want to buy back)
            value = wp.bid_price - sp.ask_price - sc.ask_price + wc.bid_price
            return value
        except:
            return None

    # -------- HELPERS -------------------------------------------------------
    def get_iv_rank(self):
        """1-year IV-rank proxy using VIX high/low."""
        hist = self.history(self.vix, 252, Resolution.DAILY)
        if hist.empty: return None
        vMin, vMax = hist["close"].min(), hist["close"].max()
        vNow = self.securities[self.vix].price
        return (vNow - vMin) / (vMax - vMin) if vMax > vMin else None

    def get_contract(self, chain, strike, right, expiry):
        """Return contract matching strike/right/expiry, else None."""
        for c in chain:
            if (abs(c.strike - strike) < 1e-6 and
                c.right == right and
                c.expiry == expiry):
                return c
        return None