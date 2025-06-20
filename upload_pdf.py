#!/usr/bin/env python3
"""
PDF Upload Script - CLI tool to upload and process PDFs without using the web UI.
Usage: python upload_pdf.py <path_to_pdf_file>
"""

import sys
import os
import asyncio
import shutil
from pathlib import Path

# Change to backend directory so database paths work correctly
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(script_dir, 'backend')
os.chdir(backend_dir)

# Add backend to path
sys.path.insert(0, backend_dir)

from backend.app.database import SessionLocal, PDFDocument, Base, engine
from backend.app.pdf_processor import PDFProcessor
from backend.app.vector_store import VectorStore

class PDFUploader:
    def __init__(self):
        # Initialize components
        self.pdf_processor = PDFProcessor()
        self.vector_store = VectorStore()
        
        # Ensure database tables exist
        Base.metadata.create_all(bind=engine)
        
        # Create uploads directory if it doesn't exist
        self.uploads_dir = os.path.join(os.path.dirname(__file__), 'backend', 'uploads')
        os.makedirs(self.uploads_dir, exist_ok=True)
    
    def upload_and_process_pdf(self, pdf_path: str) -> bool:
        """Upload and process a PDF file."""
        try:
            # Validate PDF file exists
            if not os.path.exists(pdf_path):
                print(f"❌ Error: File not found: {pdf_path}")
                return False
            
            # Validate it's a PDF file
            if not pdf_path.lower().endswith('.pdf'):
                print(f"❌ Error: File must be a PDF: {pdf_path}")
                return False
            
            # Get file info
            file_size = os.path.getsize(pdf_path)
            filename = os.path.basename(pdf_path)
            
            print(f"📁 Processing PDF: {filename}")
            print(f"📊 File size: {file_size:,} bytes")
            
            # Check if file already exists in database
            db = SessionLocal()
            try:
                existing_doc = db.query(PDFDocument).filter(PDFDocument.filename == filename).first()
                if existing_doc:
                    print(f"⚠️  Warning: Document '{filename}' already exists in database")
                    response = input("Do you want to reprocess it? (y/N): ")
                    if response.lower() != 'y':
                        print("❌ Upload cancelled")
                        return False
                    
                    # Delete existing document
                    db.delete(existing_doc)
                    db.commit()
                    print("🗑️  Deleted existing document record")
                
                # Copy file to uploads directory
                dest_path = os.path.join(self.uploads_dir, filename)
                shutil.copy2(pdf_path, dest_path)
                print(f"📋 Copied file to: {dest_path}")
                
                # Create database record
                pdf_document = PDFDocument(
                    filename=filename,
                    file_path=dest_path,
                    file_size=file_size,
                    processing=True,
                    processed=False
                )
                
                db.add(pdf_document)
                db.commit()
                db.refresh(pdf_document)
                
                print(f"💾 Created database record with ID: {pdf_document.id}")
                
                # Process the PDF
                print("🔄 Starting PDF processing...")
                success = asyncio.run(self._process_pdf_async(pdf_document.id, dest_path, filename))
                
                if success:
                    print("✅ PDF processing completed successfully!")
                    print(f"📚 Document '{filename}' is now available for searching")
                    return True
                else:
                    print("❌ PDF processing failed!")
                    return False
                    
            finally:
                db.close()
                
        except Exception as e:
            print(f"❌ Error during upload: {str(e)}")
            return False
    
    async def _process_pdf_async(self, pdf_id: int, pdf_path: str, filename: str) -> bool:
        """Process PDF using the existing PDFProcessor method."""
        try:
            # Use the existing process_pdf method from PDFProcessor
            await self.pdf_processor.process_pdf(pdf_id, pdf_path, filename)
            print("✨ PDF processing completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during processing: {str(e)}")
            return False

def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python upload_pdf.py <path_to_pdf_file>")
        print("Example: python upload_pdf.py \"C:\\Documents\\my_book.pdf\"")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    print("🚀 PDF Upload and Processing Tool")
    print("=" * 40)
    
    uploader = PDFUploader()
    success = uploader.upload_and_process_pdf(pdf_path)
    
    if success:
        print("\n🎉 Success! Your PDF has been uploaded and processed.")
        print("You can now search for content using:")
        print("- The web interface at http://localhost:8000")
        print("- Claude Desktop MCP tools")
        print("- Cursor MCP integration")
    else:
        print("\n💥 Failed to upload and process PDF.")
        sys.exit(1)

if __name__ == "__main__":
    main()