#!/usr/bin/env python3

import os
import json
import subprocess
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

QC_USER_ID = os.environ.get('QC_USER_ID', '')
QC_TOKEN = os.environ.get('QC_TOKEN', '')

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "service": "mcp-trader",
        "version": "1.0.0",
        "qc_user_id": QC_USER_ID[:6] + "..." if QC_USER_ID else "not set"
    })

@app.route('/compile', methods=['POST'])
def compile_project():
    data = request.json
    project = data.get('project', 'IronCondor')
    
    try:
        result = subprocess.run(
            ['lean', 'cloud', 'build', project, '--output', 'build.json'],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "status": "success" if result.returncode == 0 else "failed",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/backtest', methods=['POST'])
def backtest_project():
    data = request.json
    project = data.get('project', 'IronCondor')
    
    try:
        result = subprocess.run(
            ['lean', 'cloud', 'backtest', project, '-o', 'result.json'],
            capture_output=True,
            text=True
        )
        
        return jsonify({
            "status": "success" if result.returncode == 0 else "failed",
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
    file_path = data.get('file_path', '')
    
    return jsonify({
        "status": "success",
        "message": "Auto-fix functionality to be implemented",
        "errors_received": len(errors)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)