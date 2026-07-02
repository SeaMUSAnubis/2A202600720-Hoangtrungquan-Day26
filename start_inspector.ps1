$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Server = Join-Path $Root "implementation\mcp_server.py"
npx -y @modelcontextprotocol/inspector python $Server
