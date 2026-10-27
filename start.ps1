# AI Study Agent Launcher Script
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  🧠 Starting AI Study Agent System       " -ForegroundColor Yellow
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Ensure Qdrant Vector DB is running
$qdrant = docker ps --filter "name=qdrant" --format "{{.Names}}"
if (-not $qdrant) {
    Write-Host "Starting Qdrant Vector Store..." -ForegroundColor Gray
    docker start qdrant 2>$null
    if ($LASTEXITCODE -ne 0) {
        docker run -d --name qdrant -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage --restart unless-stopped qdrant/qdrant:latest
    }
} else {
    Write-Host "✅ Qdrant Vector Store is running on port 6333" -ForegroundColor Green
}

# 2. Start FastAPI Server
Write-Host "Starting FastAPI Study Agent & Web Dashboard..." -ForegroundColor Gray
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $currentDir
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
