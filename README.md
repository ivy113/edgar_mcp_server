# EdgarTools MCP Server

An MCP (Model Context Protocol) server that provides access to SEC EDGAR filing data through the powerful [edgartools](https://github.com/dgunning/edgartools) library.

## Features

- **Company Information**: Get basic company details and recent filings
- **Filing Retrieval**: Access and filter SEC filings by form type
- **Financial Data**: Extract structured financial statements from 10-K/10-Q filings
- **Insider Trading**: Monitor insider transactions through Form 4 filings
- **Text Extraction**: Get clean text from filings for analysis
- **SEC Compliance**: Built-in identity management for SEC requirements




## MCP Server IDE Setup Example

If you are integrating this server with an IDE that supports MCP servers, you might configure your `mcp.json` like this:

```json
{
  "mcpServers": {
    
    "edgartools-mcp": {
      "command": "/path/to/your/edgar_mcp_server/.venv/bin/python",
      "args": ["-m", "edgar_mcp_server.server"],
      "env": {
        "PYTHONPATH": "/path/to/your/edgar_mcp_server/src",
        "EDGAR_USER_EMAIL": "your_email@example.com"
      }
    }
  }
}
```

**Notes:**
- Replace `/path/to/your/edgar_mcp_server/` with the actual path where you have cloned or installed the `edgar_mcp_server` project.
- The `"command"` should point to the Python executable in your virtual environment.
- The `"PYTHONPATH"` should point to the `src` directory inside your `edgar_mcp_server`.
- Set `"EDGAR_USER_EMAIL"` to your own email address for EDGAR access.

