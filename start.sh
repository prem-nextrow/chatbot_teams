echo "Starting MCP server..."
python tools/mcp_server.py &

echo "Waiting for MCP to be ready..."
sleep 3

echo "Starting FastAPI..."
uvicorn app:app --host 0.0.0.0 --port 8003
