#!/bin/bash

# Navigate to project directory
cd "/Users/abdullahzewaid/Desktop/option strategies"

echo "🚀 Starting Iron Condor Trading Automation..."
echo "=================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# Start MCP server
echo "📦 Starting MCP server..."
docker-compose up -d

# Wait for server to be ready
echo "⏳ Waiting for MCP server to be ready..."
sleep 5

# Check if MCP server is running
if curl -s http://localhost:8000/ > /dev/null; then
    echo "✅ MCP Server is running!"
    echo ""
    echo "📊 Server status:"
    curl -s http://localhost:8000/ | python -m json.tool
    echo ""
    echo "=================================="
    echo "✅ Setup complete! You can now run:"
    echo "   python auto_runner.py"
    echo ""
    echo "Or manually test with:"
    echo "   lean cloud backtest IronCondor --open"
else
    echo "❌ MCP Server failed to start. Check logs with:"
    echo "   docker logs mcp-trader"
fi