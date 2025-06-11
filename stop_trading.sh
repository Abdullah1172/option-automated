#!/bin/bash

# Navigate to project directory
cd "/Users/abdullahzewaid/Desktop/option strategies"

echo "🛑 Stopping Iron Condor Trading Automation..."
echo "=================================="

# Stop MCP server
echo "📦 Stopping MCP server..."
docker-compose down

echo "✅ All services stopped!"