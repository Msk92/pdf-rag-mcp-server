# PDF Upload Script for Windows PowerShell
# Usage: .\upload_pdf.ps1 "path\to\your\file.pdf"

param(
    [Parameter(Mandatory=$true)]
    [string]$PdfPath
)

# Check if file exists
if (-not (Test-Path $PdfPath)) {
    Write-Host "❌ Error: File not found: $PdfPath" -ForegroundColor Red
    exit 1
}

# Check if file is a PDF
if (-not $PdfPath.EndsWith(".pdf", [System.StringComparison]::OrdinalIgnoreCase)) {
    Write-Host "❌ Error: File must be a PDF: $PdfPath" -ForegroundColor Red
    exit 1
}

# Change to script directory
Set-Location $PSScriptRoot

Write-Host "🚀 Starting PDF upload and processing..." -ForegroundColor Green

# Run the Python upload script
try {
    & uv run upload_pdf.py $PdfPath
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ PDF upload completed successfully!" -ForegroundColor Green
    } else {
        Write-Host "`n❌ PDF upload failed!" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Error running upload script: $_" -ForegroundColor Red
    exit 1
}