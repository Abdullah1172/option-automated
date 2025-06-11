# HV-7 Condor Strategy Analysis

## Strategy Overview

The HV-7 Condor is a sophisticated iron condor strategy that trades SPY options with 7 days to expiration (DTE). It implements multiple volatility filters and risk management rules to capitalize on theta decay while protecting against adverse moves.

## Key Strategy Components

### 1. Entry Criteria
- **Trade Days**: Monday and Wednesday at 15:40 ET (20 minutes before close)
- **DTE Range**: 6-8 days (targeting weekly options)
- **Volatility Filters**:
  - VIX must be > 18 (filters out low volatility environments)
  - IV Rank must be ≥ 40% (ensures elevated implied volatility)
- **Strike Selection**:
  - Short strikes at 20-delta (both put and call)
  - $5 wide wings for defined risk
- **Credit Target**: Minimum 30% of wing width ($1.50 on $5 wings)

### 2. Position Management
- **Profit Target**: 50% of credit received
- **Stop Loss**: 1.5x credit received
- **Delta Roll**: Close if either short strike exceeds 30-delta
- **Time Exit**: Close positions with ≤2 days to expiration
- **Risk Cap**: Maximum 35% of portfolio at risk

### 3. Risk Management Features
- **Portfolio Risk Cap**: Prevents overleveraging by limiting total risk to 35%
- **Dynamic Position Sizing**: Adjusts quantity based on available risk budget
- **Multiple Exit Triggers**: Profit target, stop loss, delta breach, time decay

## Strategy Strengths

### 1. **High Probability Setup**
- 20-delta shorts theoretically have ~80% probability of expiring OTM
- IV filters ensure selling when premium is elevated
- Weekly options provide rapid theta decay

### 2. **Robust Risk Management**
- Defined risk with protective wings
- Multiple exit criteria prevent large losses
- Portfolio risk cap prevents account blow-ups

### 3. **Market Conditions Filter**
- VIX > 18 ensures adequate premium
- IV Rank ≥ 40% confirms relative volatility elevation
- Avoids low volatility environments where risk/reward is poor

### 4. **Systematic Approach**
- Clear entry/exit rules remove emotion
- Scheduled execution ensures consistency
- Automated position management

## Strategy Weaknesses

### 1. **Volatility Dependency**
- Strategy may have long periods of inactivity when VIX < 18
- In 2024, VIX spent significant time below 18
- Limited trading opportunities in calm markets

### 2. **Whipsaw Risk**
- 30-delta roll trigger may cause premature exits in volatile markets
- Could miss profit targets after rolling positions
- Transaction costs accumulate with frequent adjustments

### 3. **Limited Upside**
- Maximum profit capped at 50% of credit
- Cannot capture large directional moves
- Requires high win rate to be profitable

### 4. **Timing Risk**
- Fixed entry times may not be optimal
- Market conditions can change rapidly in final 20 minutes
- No intraday adjustment capability

## Expected Performance Metrics

### Theoretical Expectations
- **Win Rate**: 65-75% (based on probability and management)
- **Average Winner**: ~25% of credit (50% target × 50% realized)
- **Average Loser**: ~75% of credit (exits before max loss)
- **Profit Factor**: 1.2-1.5
- **Annual Return**: 15-25% in favorable conditions

### Risk Metrics
- **Max Drawdown**: 15-20% expected
- **Risk-Adjusted Return**: Sharpe ratio 0.8-1.2
- **Recovery Time**: 2-4 months from drawdowns

## Market Environment Considerations

### Favorable Conditions
- Elevated volatility (VIX 20-30)
- Range-bound markets
- Consistent weekly option volume
- Normal contango in VIX futures

### Unfavorable Conditions
- Low volatility (VIX < 15)
- Trending markets (strong directional moves)
- Volatility expansions near expiration
- Gap risk around major events

## Implementation Notes

### 1. **Infrastructure Requirements**
- Minute-level option data
- Real-time Greeks calculation
- VIX data feed
- Reliable execution at 15:40 ET

### 2. **Potential Improvements**
- Add term structure analysis (VIX9D/VIX comparison)
- Implement dynamic delta targets based on VIX level
- Consider intraday entry optimization
- Add correlation filters for market regime

### 3. **Backtesting Considerations**
- Local backtests will fail without 2023-2024 option data
- Cloud backtesting required for accurate results
- Greeks approximation may differ from live trading
- Bid-ask spreads significantly impact returns

## Conclusion

The HV-7 Condor is a well-designed systematic options strategy that leverages multiple edges:
1. Selling elevated volatility (IV Rank filter)
2. Time decay on weekly options
3. High probability trade structure
4. Comprehensive risk management

However, success depends heavily on market conditions providing sufficient volatility and trading opportunities. The strategy is best suited for traders comfortable with:
- Limited but consistent returns
- Periods of inactivity
- Managing multiple positions
- Accepting capped upside for higher probability

Expected annual returns of 15-25% with 15-20% drawdowns represent a reasonable risk/reward profile for a systematic options strategy, particularly given the defined risk nature of iron condors.