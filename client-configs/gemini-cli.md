# Gemini CLI MCP setup

Replace the Python path with the interpreter where dependencies are installed.

```bash
gemini mcp add sqlite-lab python "/ABSOLUTE/PATH/TO/Day26-Track3-MCP-tool-integration/implementation/mcp_server.py" --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server and show me the top 2 students by score."
```
