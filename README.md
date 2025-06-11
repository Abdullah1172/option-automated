# QuantConnect MCP Setup

This directory contains the MCP (Model Context Protocol) setup for running QuantConnect backtests.

## Setup Complete! ✓

Your environment is now configured and connected to QuantConnect API.

## Quick Start

1. **Activate the environment:**
   ```bash
   source quantconnect_env/bin/activate
   ```

2. **Run a test strategy:**
   ```bash
   python run_strategy.py
   ```

3. **Run your own strategy:**
   ```bash
   python run_strategy.py your_strategy.py
   ```

## Files

- `quantconnect_client.py` - Main API client for QuantConnect
- `run_strategy.py` - Strategy runner with analysis
- `setup-mcp` - Environment setup script
- `quantconnect_env/` - Python virtual environment

## Your Credentials

- User ID: 386972
- API Token: Configured in environment

## Example Strategy Format

Your strategy files should follow the QuantConnect algorithm format:

```python
from AlgorithmImports import *

class YourStrategyName(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2024, 1, 1)
        self.SetCash(100000)
        # Add your initialization code
        
    def OnData(self, data):
        # Add your trading logic
        pass
```

## Ready to Use!

You can now provide your option strategy code and I'll run the backtest for you.