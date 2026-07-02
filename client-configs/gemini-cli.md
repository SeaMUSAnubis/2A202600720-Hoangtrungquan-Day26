# Gemini CLI MCP setup

This example uses the virtual environment in this repository. Update both paths if you move the project.

```powershell
gemini mcp add sqlite-lab "D:\2 Code\4 Expert\Day26\Day26-Track3-MCP-tool-integration\.venv\Scripts\python.exe" "D:\2 Code\4 Expert\Day26\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py" --description "SQLite lab FastMCP server" --timeout 10000
gemini mcp list
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Use the sqlite-lab MCP server and show me the top 2 students by score."
```
