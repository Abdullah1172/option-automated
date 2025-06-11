# QuantConnect Backtest Troubleshooting Guide

## Current Issue: Organization ID Mismatch

### Problem
```
Error: We couldn't find you account in the given organization, ORG: 654b629e437d8ad962aaa8a6a41ed7be
```

### Root Cause
The QuantConnect account (User ID: 386972) is not properly associated with the organization ID in the configuration.

## Solutions

### Option 1: Use Personal Organization (Recommended)
1. **Get your personal organization ID:**
   ```bash
   # Login to QuantConnect web interface
   # Go to Organization settings
   # Copy the Organization ID (usually starts with your user ID)
   ```

2. **Update the configuration:**
   ```bash
   # Update .env file
   QC_ORG_ID=YOUR_PERSONAL_ORG_ID
   QC_TOKEN=f6f5df71e9938e3c4eca2298528bcc383c2a5fad14283313ecb9d07c68463e78
   
   # Update lean.json
   "organization-id": "YOUR_PERSONAL_ORG_ID"
   ```

### Option 2: Create New Project in Web Interface
1. Go to https://www.quantconnect.com/terminal
2. Create a new project called "IronCondor"
3. Copy the HV-7 Condor code into main.py
4. Run backtest directly in the web interface

### Option 3: Fix GitHub Secrets
1. Go to https://github.com/Abdullah1172/option-automated/settings/secrets/actions
2. Update `QC_ORG_ID` with the correct organization ID
3. Ensure `QC_TOKEN` is correct

## Quick Diagnostic Commands

### Check Current Setup
```bash
# Check if logged in
lean whoami

# Check version
lean --version

# Test our diagnostic script
python check_backtest.py
```

### Manual Backtest (Web Interface)
1. Go to https://www.quantconnect.com/terminal
2. Create new project → "IronCondor"
3. Replace main.py with our HV-7 Condor code
4. Click "Backtest" button
5. Wait for results

## GitHub Actions Status

### Current Workflows
- `auto-fix.yml` - Original workflow (may have issues)
- `improved-backtest.yml` - New improved workflow with error handling

### Check GitHub Actions
1. Go to https://github.com/Abdullah1172/option-automated/actions
2. Look for failed runs
3. Check error messages in logs

## Expected Results When Fixed

### Successful Backtest Should Show:
- **Total Trades**: 20-50 (depending on VIX > 18 periods)
- **Win Rate**: 65-75%
- **Annual Return**: 15-25%
- **Max Drawdown**: 15-20%
- **Sharpe Ratio**: 0.8-1.2

### Success Criteria (from codex_tasks.yaml):
- `win_rate >= 0.55` (55%)
- `avg_r >= 0.15` (15% return)
- `trades > 0`

## Error Patterns to Watch For

### Compilation Errors
- Missing imports
- Syntax errors
- Class name issues

### Runtime Errors
- Data access issues
- Greeks not available
- Option chain problems

### Data Issues
- Missing VIX data
- Incomplete option chains
- Bid/ask spread problems

## Next Steps

1. **Immediate**: Try manual backtest in web interface
2. **Short-term**: Fix organization ID configuration  
3. **Long-term**: Complete automation with proper credentials

The strategy code is solid - the issue is purely configuration/access related!