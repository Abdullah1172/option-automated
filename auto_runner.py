#!/usr/bin/env python3

import time
import json
import requests
import subprocess
from datetime import datetime

MCP_URL = "http://localhost:8000"
MAX_ITERATIONS = 10
PROJECT_NAME = "IronCondor"

def log(message):
    """Log message with timestamp"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")

def check_mcp_server():
    """Check if MCP server is running"""
    try:
        response = requests.get(f"{MCP_URL}/")
        return response.status_code == 200
    except:
        return False

def run_backtest():
    """Run backtest via MCP server"""
    log("Running backtest...")
    response = requests.post(f"{MCP_URL}/backtest", json={"project": PROJECT_NAME})
    return response.json()

def apply_fixes(errors):
    """Apply auto-fixes via MCP server"""
    log(f"Applying fixes for {len(errors)} errors...")
    response = requests.post(f"{MCP_URL}/fix", json={
        "errors": errors,
        "file_path": f"{PROJECT_NAME}/main.py"
    })
    return response.json()

def analyze_results():
    """Analyze backtest results"""
    log("Analyzing results...")
    response = requests.post(f"{MCP_URL}/analyze", json={"result_file": "result.json"})
    return response.json()

def main():
    """Main automation loop"""
    log("Starting automated Iron Condor optimization...")
    
    # Check MCP server
    if not check_mcp_server():
        log("ERROR: MCP server not running. Start it with: docker-compose up")
        return
    
    log("MCP server is running")
    
    iteration = 0
    success = False
    
    while iteration < MAX_ITERATIONS and not success:
        iteration += 1
        log(f"\n=== Iteration {iteration}/{MAX_ITERATIONS} ===")
        
        # Run backtest
        backtest_result = run_backtest()
        
        if backtest_result['status'] == 'success':
            log("Backtest completed successfully")
            
            # Analyze results
            analysis = analyze_results()
            
            if analysis['status'] == 'success':
                log(f"Metrics: {json.dumps(analysis['metrics'], indent=2)}")
                
                if analysis['all_criteria_met']:
                    log("SUCCESS! All criteria met:")
                    log(f"  - Win Rate: {analysis['metrics']['win_rate']:.2%} (>= 55%)")
                    log(f"  - Total Trades: {analysis['metrics']['total_trades']} (> 0)")
                    success = True
                else:
                    log("Criteria not met:")
                    for criterion, met in analysis['criteria_met'].items():
                        log(f"  - {criterion}: {'✓' if met else '✗'}")
                    
                    # Could implement strategy adjustments here
                    log("Adjusting strategy parameters...")
                    # TODO: Implement parameter optimization
                    
        elif backtest_result['status'] == 'failed':
            log("Backtest failed with errors")
            
            if backtest_result.get('can_autofix'):
                # Apply fixes
                fix_result = apply_fixes(backtest_result['errors'])
                
                if fix_result['status'] == 'success':
                    log(f"Applied {len(fix_result['fixes_applied'])} fixes:")
                    for fix in fix_result['fixes_applied']:
                        log(f"  - {fix}")
                else:
                    log(f"Failed to apply fixes: {fix_result.get('message')}")
                    break
            else:
                log("Errors cannot be auto-fixed")
                log(f"Error details: {backtest_result.get('stderr', '')}")
                break
        
        else:
            log(f"Unexpected status: {backtest_result['status']}")
            break
        
        # Add delay between iterations
        if not success and iteration < MAX_ITERATIONS:
            log("Waiting 5 seconds before next iteration...")
            time.sleep(5)
    
    if success:
        log("\n✅ OPTIMIZATION COMPLETE - All criteria met!")
    else:
        log("\n❌ OPTIMIZATION FAILED - Maximum iterations reached or unrecoverable error")
    
    # Save final state
    with open('optimization_log.json', 'w') as f:
        json.dump({
            'iterations': iteration,
            'success': success,
            'timestamp': datetime.now().isoformat()
        }, f, indent=2)

if __name__ == "__main__":
    main()