#!/usr/bin/env python3
"""
Entry point for MCP server for Claude Desktop integration.
This script can be called directly by Claude Desktop.
"""

import sys
import os
import asyncio

# Add the backend directory to the Python path
backend_path = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_path)

from backend.app.mcp_server import main

if __name__ == "__main__":
    asyncio.run(main())