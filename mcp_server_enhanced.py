#!/usr/bin/env python3

import os
import re
import json
import subprocess
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

QC_USER_ID = os.environ.get('QC_USER_ID', '')
QC_TOKEN = os.environ.get('QC_TOKEN', '')

# Common error patterns and fixes
ERROR_PATTERNS = {
    r"The type or namespace name '(\w+)' could not be found": {
        "fix": "add_import",
        "imports": {
            "OptionStrategies": "from AlgorithmImports import OptionStrategies",
            "Resolution": "from AlgorithmImports import Resolution",
            "Slice": "from AlgorithmImports import Slice",
            "QCAlgorithm": "from AlgorithmImports import QCAlgorithm",
            "timedelta": "from datetime import timedelta"
        }
    },
    r"'(\w+)' is not defined": {
        "fix": "add_import",
        "imports": {
            "OptionStrategies": "from AlgorithmImports import OptionStrategies",
            "Resolution": "from AlgorithmImports import Resolution",
            "Slice": "from AlgorithmImports import Slice",
            "QCAlgorithm": "from AlgorithmImports import QCAlgorithm",
            "timedelta": "from datetime import timedelta"
        }
    },
    r"AttributeError: '(\w+)' object has no attribute '(\w+)'": {
        "fix": "fix_attribute",
        "mappings": {
            "Buy": "buy",
            "SetFilter": "set_filter",
            "AddOption": "add_option",
            "AddEquity": "add_equity"
        }
    },
    r"Invalid syntax": {
        "fix": "fix_syntax"
    },
    r"IndentationError": {
        "fix": "fix_indentation"
    }
}

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "mcp-trader-enhanced",
        "version": "2.0.0",
        "qc_user_id": QC_USER_ID[:6] + "..." if QC_USER_ID else "not set",
        "features": ["compile", "backtest", "auto-fix", "analyze"]
    })

@app.route('/compile', methods=['POST'])
def compile_project():
    data = request.json
    project = data.get('project', 'IronCondor')
    
    try:
        # First push to cloud
        push_result = subprocess.run(
            ['lean', 'cloud', 'push', '--project', project],
            capture_output=True,
            text=True
        )
        
        if push_result.returncode != 0:
            return jsonify({
                "status": "failed",
                "phase": "push",
                "stdout": push_result.stdout,
                "stderr": push_result.stderr,
                "returncode": push_result.returncode
            })
        
        # Then compile in cloud (there's no direct build command, use backtest with compile-only flag)
        return jsonify({
            "status": "success",
            "message": "Project pushed successfully. Use backtest endpoint to compile and run.",
            "stdout": push_result.stdout
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/backtest', methods=['POST'])
def backtest_project():
    data = request.json
    project = data.get('project', 'IronCondor')
    
    try:
        result = subprocess.run(
            ['lean', 'cloud', 'backtest', project, '--open', '--push'],
            capture_output=True,
            text=True
        )
        
        # Parse output for errors
        if result.returncode != 0:
            errors = parse_errors(result.stderr + result.stdout)
            return jsonify({
                "status": "failed",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "errors": errors,
                "can_autofix": len(errors) > 0
            })
        
        return jsonify({
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/fix', methods=['POST'])
def fix_errors():
    data = request.json
    errors = data.get('errors', [])
    file_path = data.get('file_path', 'IronCondor/main.py')
    
    if not errors:
        # Try to get errors from the last backtest
        result = get_last_errors()
        if result:
            errors = result.get('errors', [])
    
    if not errors:
        return jsonify({
            "status": "no_errors",
            "message": "No errors to fix"
        })
    
    fixes_applied = []
    
    try:
        # Read the current file
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Apply fixes
        for error in errors:
            fix = apply_fix(content, error)
            if fix:
                content = fix['content']
                fixes_applied.append(fix['description'])
        
        # Write back the fixed content
        with open(file_path, 'w') as f:
            f.write(content)
        
        return jsonify({
            "status": "success",
            "fixes_applied": fixes_applied,
            "message": f"Applied {len(fixes_applied)} fixes"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/analyze', methods=['POST'])
def analyze_results():
    data = request.json
    result_file = data.get('result_file', 'result.json')
    
    try:
        with open(result_file, 'r') as f:
            results = json.load(f)
        
        # Extract key metrics
        metrics = {
            "total_trades": results.get("totalOrders", 0),
            "win_rate": calculate_win_rate(results),
            "sharpe_ratio": results.get("sharpeRatio", 0),
            "total_return": results.get("totalReturn", 0),
            "max_drawdown": results.get("maxDrawdown", 0)
        }
        
        # Check against criteria
        criteria_met = {
            "win_rate": metrics["win_rate"] >= 0.55,
            "avg_r": metrics.get("avg_return", 0) >= 0.15,
            "trades": metrics["total_trades"] > 0
        }
        
        return jsonify({
            "status": "success",
            "metrics": metrics,
            "criteria_met": criteria_met,
            "all_criteria_met": all(criteria_met.values())
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def parse_errors(output):
    """Parse errors from compiler/runtime output"""
    errors = []
    lines = output.split('\n')
    
    for i, line in enumerate(lines):
        for pattern, fix_info in ERROR_PATTERNS.items():
            match = re.search(pattern, line)
            if match:
                error = {
                    "line": i,
                    "message": line,
                    "pattern": pattern,
                    "fix_type": fix_info["fix"],
                    "match_groups": match.groups()
                }
                errors.append(error)
    
    return errors

def apply_fix(content, error):
    """Apply a specific fix to the content"""
    fix_type = error.get('fix_type')
    
    if fix_type == 'add_import':
        # Add missing import
        missing_name = error['match_groups'][0] if error['match_groups'] else None
        if missing_name and missing_name in ERROR_PATTERNS[error['pattern']]['imports']:
            import_line = ERROR_PATTERNS[error['pattern']]['imports'][missing_name]
            if import_line not in content:
                # Add after other imports
                lines = content.split('\n')
                import_index = 0
                for i, line in enumerate(lines):
                    if line.startswith('from ') or line.startswith('import '):
                        import_index = i + 1
                
                lines.insert(import_index, import_line)
                return {
                    'content': '\n'.join(lines),
                    'description': f"Added import: {import_line}"
                }
    
    elif fix_type == 'fix_attribute':
        # Fix attribute name
        if len(error['match_groups']) >= 2:
            wrong_attr = error['match_groups'][1]
            mappings = ERROR_PATTERNS[error['pattern']]['mappings']
            if wrong_attr in mappings:
                correct_attr = mappings[wrong_attr]
                content = content.replace(f'.{wrong_attr}(', f'.{correct_attr}(')
                return {
                    'content': content,
                    'description': f"Fixed attribute: {wrong_attr} -> {correct_attr}"
                }
    
    elif fix_type == 'fix_syntax':
        # Basic syntax fixes
        # Fix missing colons
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in ['def ', 'if ', 'for ', 'while ', 'class ']):
                if not line.strip().endswith(':') and not line.strip().endswith('\\'):
                    lines[i] = line.rstrip() + ':'
        
        return {
            'content': '\n'.join(lines),
            'description': "Fixed syntax issues"
        }
    
    elif fix_type == 'fix_indentation':
        # Fix indentation
        lines = content.split('\n')
        fixed_lines = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if stripped:
                if stripped.startswith(('def ', 'class ', 'if ', 'for ', 'while ', 'try:', 'except')):
                    fixed_lines.append('    ' * indent_level + stripped)
                    if stripped.endswith(':'):
                        indent_level += 1
                elif stripped in ['else:', 'elif:', 'except:', 'finally:']:
                    indent_level = max(0, indent_level - 1)
                    fixed_lines.append('    ' * indent_level + stripped)
                    indent_level += 1
                elif stripped == 'return' or stripped.startswith('return '):
                    fixed_lines.append('    ' * indent_level + stripped)
                    indent_level = max(0, indent_level - 1)
                else:
                    fixed_lines.append('    ' * indent_level + stripped)
            else:
                fixed_lines.append('')
        
        return {
            'content': '\n'.join(fixed_lines),
            'description': "Fixed indentation"
        }
    
    return None

def get_last_errors():
    """Get errors from the last run"""
    # This would typically read from a log file or database
    # For now, return None
    return None

def calculate_win_rate(results):
    """Calculate win rate from results"""
    trades = results.get('trades', [])
    if not trades:
        return 0
    
    winning_trades = sum(1 for trade in trades if trade.get('profit', 0) > 0)
    return winning_trades / len(trades) if trades else 0

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)