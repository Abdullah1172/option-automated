#!/usr/bin/env python3
"""
Script to check QuantConnect backtest results and common errors
"""

import subprocess
import json
import sys
import os
from datetime import datetime

def run_command(cmd, description):
    """Run a command and return result"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
        return result
    except subprocess.TimeoutExpired:
        print(f"❌ Command timed out: {cmd}")
        return None
    except Exception as e:
        print(f"❌ Error running command: {e}")
        return None

def check_lean_status():
    """Check if Lean CLI is working"""
    result = run_command("lean --version", "Checking Lean CLI version")
    if result and result.returncode == 0:
        print(f"✅ Lean CLI: {result.stdout.strip()}")
        return True
    else:
        print("❌ Lean CLI not working")
        return False

def check_login_status():
    """Check if logged into QuantConnect"""
    result = run_command("lean whoami", "Checking QuantConnect login")
    if result and result.returncode == 0:
        print(f"✅ Logged in as: {result.stdout.strip()}")
        return True
    else:
        print("❌ Not logged into QuantConnect")
        return False

def try_push_project():
    """Try to push the project"""
    result = run_command('lean cloud push --project "IronCondor"', "Pushing project to cloud")
    if result:
        if result.returncode == 0:
            print("✅ Project pushed successfully")
            return True
        else:
            print("❌ Failed to push project:")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
    return False

def try_backtest():
    """Try to run backtest"""
    result = run_command('lean cloud backtest "IronCondor" --open', "Running cloud backtest")
    if result:
        print(f"📊 Backtest finished with exit code: {result.returncode}")
        print(f"\n📋 Output:\n{result.stdout}")
        if result.stderr:
            print(f"\n⚠️ Errors:\n{result.stderr}")
        
        # Analyze output for common issues
        output_text = result.stdout + result.stderr
        
        if "compilation" in output_text.lower():
            print("\n🔧 Compilation issues detected")
        if "runtime" in output_text.lower():
            print("\n🔧 Runtime issues detected")
        if "data" in output_text.lower() and "missing" in output_text.lower():
            print("\n🔧 Data issues detected")
            
        return result.returncode == 0
    return False

def main():
    """Main check routine"""
    print("🚀 QuantConnect Backtest Checker")
    print("=" * 40)
    
    # Check prerequisites
    if not check_lean_status():
        print("\n❌ Please install Lean CLI: pip install lean")
        return False
    
    if not check_login_status():
        print("\n❌ Please login to QuantConnect:")
        print("lean login --user-id YOUR_ORG_ID --api-token YOUR_TOKEN")
        return False
    
    # Try to push and backtest
    print("\n" + "=" * 40)
    if not try_push_project():
        print("\n❌ Cannot proceed without successful push")
        return False
    
    print("\n" + "=" * 40)
    success = try_backtest()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All checks passed! Backtest completed successfully.")
    else:
        print("❌ Issues detected. Check the output above for details.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)