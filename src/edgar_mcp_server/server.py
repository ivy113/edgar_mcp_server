#!/usr/bin/env python3
"""
MCP Server for EdgarTools - SEC Filing Data Access
Provides tools for accessing SEC EDGAR filings data through the edgartools library
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

try:
    from edgar import Company, set_identity, get_filings
    # from edgar.entities import Filing
    EDGARTOOLS_AVAILABLE = True
except ImportError:
    EDGARTOOLS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("edgartools-mcp-server")

app = Server("edgartools-mcp-server")

# Global configuration
IDENTITY_SET = False
USER_EMAIL = None

# Check for required environment variable
EDGAR_USER_EMAIL = os.getenv('EDGAR_USER_EMAIL')
if not EDGAR_USER_EMAIL:
    logger.error("EDGAR_USER_EMAIL environment variable is required")
    raise ValueError("EDGAR_USER_EMAIL environment variable must be set")

# Set identity immediately on startup
try:
    set_identity(EDGAR_USER_EMAIL)
    IDENTITY_SET = True
    USER_EMAIL = EDGAR_USER_EMAIL
    logger.info(f"Identity set to: {EDGAR_USER_EMAIL}")
except Exception as e:
    logger.error(f"Failed to set identity: {str(e)}")
    raise


def ensure_identity():
    """Ensure user identity is set for SEC compliance"""
    global IDENTITY_SET, USER_EMAIL
    if not IDENTITY_SET:
        raise RuntimeError("User identity not set. EDGAR_USER_EMAIL environment variable is required.")


def serialize_filing_data(data: Any) -> Dict[str, Any]:
    """Convert filing data to JSON-serializable format"""
    if hasattr(data, 'to_dict'):
        return data.to_dict()
    elif hasattr(data, '__dict__'):
        result = {}
        for key, value in data.__dict__.items():
            if key.startswith('_'):
                continue
            if isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            elif isinstance(value, (date, datetime)):
                result[key] = value.isoformat()
            elif isinstance(value, list):
                result[key] = [serialize_filing_data(item) for item in value]
            elif hasattr(value, '__dict__'):
                result[key] = serialize_filing_data(value)
            else:
                result[key] = str(value)
        return result
    else:
        return str(data)


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools for SEC filing data access"""
    tools = []
    
    if not EDGARTOOLS_AVAILABLE:
        return [Tool(
            name="error",
            description="EdgarTools library not available. Please install it with: pip install edgartools",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )]
    
    tools.extend([
        Tool(
            name="get_company_info",
            description="Get basic company information and recent filings",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Company ticker symbol (e.g., AAPL, MSFT)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_company_filings",
            description="Get filings for a company with optional filtering",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Company ticker symbol"
                    },
                    "form": {
                        "type": "string",
                        "description": "Filing form type (e.g., 10-K, 10-Q, 8-K, 4)"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of filings to return",
                        "default": 10
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_filing_text",
            description="Extract text content from a specific filing",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Company ticker symbol"
                    },
                    "form": {
                        "type": "string",
                        "description": "Filing form type (e.g., 10-K, 10-Q)"
                    },
                    "filing_index": {
                        "type": "integer",
                        "description": "Index of filing to retrieve (0 for most recent)",
                        "default": 0
                    }
                },
                "required": ["ticker", "form"]
            }
        ),
        Tool(
            name="get_insider_transactions",
            description="Get insider transaction data (Form 4 filings)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Company ticker symbol"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of transactions to return",
                        "default": 20
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_financial_statements",
            description="Extract financial statements from 10-K/10-Q filings",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Company ticker symbol"
                    },
                    "form": {
                        "type": "string",
                        "description": "Filing form type (10-K or 10-Q)",
                        "enum": ["10-K", "10-Q"]
                    },
                    "filing_index": {
                        "type": "integer",
                        "description": "Index of filing to retrieve (0 for most recent)",
                        "default": 0
                    }
                },
                "required": ["ticker", "form"]
            }
        )
    ])
    
    return tools


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls"""
    
    if not EDGARTOOLS_AVAILABLE:
        return [TextContent(
            type="text",
            text="EdgarTools library not available. Please install it with: pip install edgartools"
        )]
    
    try:
        if name == "get_company_info":
            return await handle_get_company_info(arguments)
        elif name == "get_company_filings":
            return await handle_get_company_filings(arguments)
        elif name == "get_filing_text":
            return await handle_get_filing_text(arguments)
        elif name == "get_insider_transactions":
            return await handle_get_insider_transactions(arguments)
        elif name == "get_financial_statements":
            return await handle_get_financial_statements(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Error in tool {name}: {str(e)}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_company_info(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get basic company information"""
    ensure_identity()
    
    ticker = arguments.get("ticker")
    if not ticker:
        return [TextContent(type="text", text="Ticker is required")]
    
    try:
        company = Company(ticker)
        info = {
            "name": getattr(company, 'name', 'N/A'),
            "ticker": ticker,
            "cik": getattr(company, 'cik', 'N/A'),
            "sic": getattr(company, 'sic', 'N/A'),
            "industry": getattr(company, 'industry', 'N/A')
        }
        
        return [TextContent(type="text", text=json.dumps(info, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting company info: {str(e)}")]


async def handle_get_company_filings(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get company filings with optional filtering"""
    ensure_identity()
    
    ticker = arguments.get("ticker")
    form = arguments.get("form")
    limit = arguments.get("limit", 10)
    
    if not ticker:
        return [TextContent(type="text", text="Ticker is required")]
    
    try:
        company = Company(ticker)
        filings = company.get_filings()
        
        if form:
            filings = filings.filter(form=form)
        
        results = []
        for filing in filings[:limit]:
            filing_data = {
                "form": filing.form,
                "filing_date": filing.filing_date.isoformat() if hasattr(filing, 'filing_date') else 'N/A',
                "accession_number": getattr(filing, 'accession_number', 'N/A'),
                "period_of_report": getattr(filing, 'period_of_report', 'N/A'),
            }
            results.append(filing_data)
        
        return [TextContent(type="text", text=json.dumps(results, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting filings: {str(e)}")]


async def handle_get_filing_text(arguments: Dict[str, Any]) -> List[TextContent]:
    """Extract text from a specific filing"""
    ensure_identity()
    
    ticker = arguments.get("ticker")
    form = arguments.get("form")
    filing_index = arguments.get("filing_index", 0)
    
    if not ticker or not form:
        return [TextContent(type="text", text="Ticker and form are required")]
    
    try:
        company = Company(ticker)
        filings = company.get_filings().filter(form=form)
        
        if filing_index >= len(filings):
            return [TextContent(type="text", text=f"Filing index {filing_index} out of range")]
        
        filing = filings[filing_index]
        text = filing.text()
        
        return [TextContent(type="text", text=text[:10000] + "..." if len(text) > 10000 else text)]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting filing text: {str(e)}")]


async def handle_get_insider_transactions(arguments: Dict[str, Any]) -> List[TextContent]:
    """Get insider transaction data"""
    ensure_identity()
    
    ticker = arguments.get("ticker")
    limit = arguments.get("limit", 20)
    
    if not ticker:
        return [TextContent(type="text", text="Ticker is required")]
    
    try:
        company = Company(ticker)
        insider_filings = company.get_filings().filter(form="4")
        
        results = []
        for filing in insider_filings[:limit]:
            try:
                insider_data = filing.obj()
                transaction_data = serialize_filing_data(insider_data)
                results.append(transaction_data)
            except Exception as e:
                logger.warning(f"Error processing insider filing: {str(e)}")
                continue
        
        return [TextContent(type="text", text=json.dumps(results, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting insider transactions: {str(e)}")]


async def handle_get_financial_statements(arguments: Dict[str, Any]) -> List[TextContent]:
    """Extract financial statements from filings"""
    ensure_identity()
    
    ticker = arguments.get("ticker")
    form = arguments.get("form")
    filing_index = arguments.get("filing_index", 0)
    
    if not ticker or not form:
        return [TextContent(type="text", text="Ticker and form are required")]
    
    try:
        company = Company(ticker)
        filings = company.get_filings().filter(form=form)
        
        if filing_index >= len(filings):
            return [TextContent(type="text", text=f"Filing index {filing_index} out of range")]
        
        filing = filings[filing_index]
        financials = filing.obj()
        
        financial_data = serialize_filing_data(financials)
        
        return [TextContent(type="text", text=json.dumps(financial_data, indent=2))]
    except Exception as e:
        return [TextContent(type="text", text=f"Error getting financial statements: {str(e)}")]


async def main():
    """Main server entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())