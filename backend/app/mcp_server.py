#!/usr/bin/env python3
"""
MCP Server for Claude Desktop integration.
Provides stdio-based MCP server that exposes PDF knowledge base functionality.
"""

import asyncio
import sys
from typing import Any, Dict, List
import json

from mcp.server.stdio import stdio_server
from mcp.server import Server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)

# Import existing app components
from .database import SessionLocal, get_db, PDFDocument, Base, engine
from .vector_store import VectorStore
from .pdf_processor import PDFProcessor
import os

# Initialize components
vector_store = VectorStore()

# Create the server
server = Server("pdf-rag-mcp")

@server.list_resources()
async def handle_list_resources() -> List[Resource]:
    """List available PDF documents as resources."""
    db = SessionLocal()
    try:
        documents = db.query(PDFDocument).filter(PDFDocument.processed == True).all()
        
        resources = []
        for doc in documents:
            resources.append(
                Resource(
                    uri=f"pdf://{doc.filename}",
                    name=doc.filename,
                    description=f"PDF document: {doc.filename}",
                    mimeType="application/pdf"
                )
            )
        return resources
    finally:
        db.close()

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read content from a PDF document."""
    if not uri.startswith("pdf://"):
        raise ValueError(f"Unsupported URI scheme: {uri}")
    
    filename = uri[6:]  # Remove "pdf://" prefix
    
    db = SessionLocal()
    try:
        document = db.query(PDFDocument).filter(
            PDFDocument.filename == filename,
            PDFDocument.processed == True
        ).first()
        
        if not document:
            raise ValueError(f"Document not found: {filename}")
        
        # For now, return basic document info
        # Full content access would require chunk storage implementation
        content_parts = [
            f"Document: {document.filename}",
            f"Pages: {document.page_count}",
            f"Status: Processed",
            f"Upload Date: {document.uploaded_at}",
            f"File Size: {document.file_size} bytes"
        ]
        
        return "\n".join(content_parts)
    finally:
        db.close()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="search_documents",
            description="Search through PDF documents using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to find relevant content in PDF documents"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 5)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="list_documents",
            description="List all available PDF documents in the knowledge base",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            }
        ),
        Tool(
            name="get_document_info",
            description="Get detailed information about a specific document",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The filename of the document to get info about"
                    }
                },
                "required": ["filename"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    
    if name == "search_documents":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        
        if not query:
            return [TextContent(type="text", text="Error: Query is required")]
        
        try:
            # Perform semantic search
            results = vector_store.search(query, k=limit)
            
            if not results:
                return [TextContent(type="text", text="No relevant documents found for your query.")]
            
            # Format results
            response_parts = [f"Found {len(results)} relevant results for query: '{query}'\n"]
            
            for i, result in enumerate(results, 1):
                # Format results from vector store
                response_parts.append(
                    f"\n--- Result {i} ---\n"
                    f"Relevance Score: {result.get('distance', 'N/A')}\n"
                    f"Content:\n{result['content']}\n"
                )
            
            return [TextContent(type="text", text="".join(response_parts))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error performing search: {str(e)}")]
    
    elif name == "list_documents":
        db = SessionLocal()
        try:
            documents = db.query(PDFDocument).all()
            
            if not documents:
                return [TextContent(type="text", text="No documents found in the knowledge base.")]
            
            response_parts = ["Available documents in the knowledge base:\n\n"]
            
            for doc in documents:
                status_emoji = "✅" if doc.processed else "⏳" if doc.processing else "❌"
                status_text = "completed" if doc.processed else "processing" if doc.processing else "failed"
                response_parts.append(
                    f"{status_emoji} {doc.filename}\n"
                    f"   Status: {status_text}\n"
                    f"   Upload Date: {doc.uploaded_at}\n"
                    f"   File Size: {doc.file_size} bytes\n\n"
                )
            
            return [TextContent(type="text", text="".join(response_parts))]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error listing documents: {str(e)}")]
        finally:
            db.close()
    
    elif name == "get_document_info":
        filename = arguments.get("filename", "")
        
        if not filename:
            return [TextContent(type="text", text="Error: Filename is required")]
        
        db = SessionLocal()
        try:
            document = db.query(PDFDocument).filter(PDFDocument.filename == filename).first()
            
            if not document:
                return [TextContent(type="text", text=f"Document '{filename}' not found.")]
            
            # Get chunk count from document
            chunk_count = document.chunks_count
            
            status_text = "completed" if document.processed else "processing" if document.processing else "failed"
            response = (
                f"Document Information: {document.filename}\n\n"
                f"Status: {status_text}\n"
                f"Upload Date: {document.uploaded_at}\n"
                f"File Size: {document.file_size} bytes\n"
                f"Number of Chunks: {chunk_count}\n"
                f"Page Count: {document.page_count}\n"
                f"File Path: {document.file_path}\n"
            )
            
            if document.processed and chunk_count > 0:
                response += f"\nDocument is ready for searching and contains {chunk_count} searchable chunks."
            elif document.processing:
                response += "\nDocument is currently being processed."
            else:
                response += "\nDocument processing may have failed or is incomplete."
            
            return [TextContent(type="text", text=response)]
            
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting document info: {str(e)}")]
        finally:
            db.close()
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Main entry point for the MCP server."""
    # Ensure we're using the correct database path (in backend folder)
    import os
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    # Point to the backend folder's database
    backend_dir = os.path.dirname(os.path.dirname(__file__))  # Go up from app/ to backend/
    db_path = os.path.join(backend_dir, 'pdf_knowledge_base.db')
    
    # Create new engine with absolute path to backend database
    global engine, SessionLocal
    engine = create_engine(
        f"sqlite:///{os.path.abspath(db_path)}",
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    
    # Run the server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())