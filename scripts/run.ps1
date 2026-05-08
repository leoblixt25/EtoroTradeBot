$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"
$PythonPath = "C:\Program Files\Python312\python.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  eToro Portfolio Manager - Starting..." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend
Write-Host "[1/2] Starting Backend (port 8000)..." -ForegroundColor Yellow
$BackendJob = Start-Job -ScriptBlock {
    param($dir, $projRoot, $py)
    Set-Location $dir
    $env:PYTHONPATH = $projRoot
    & $py -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
} -ArgumentList $BackendDir, $ProjectRoot, $PythonPath

# Start Frontend
Write-Host "[2/2] Starting Frontend (port 5173)..." -ForegroundColor Yellow
$FrontendJob = Start-Job -ScriptBlock {
    param($dir)
    Set-Location $dir
    npm run dev
} -ArgumentList $FrontendDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Both services starting up!" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop all services and exit." -ForegroundColor Gray

# Keep running and monitor jobs
try {
    while ($BackendJob.State -eq 'Running' -or $FrontendJob.State -eq 'Running') {
        Start-Sleep -Seconds 1
        Receive-Job $BackendJob -ErrorAction SilentlyContinue
        Receive-Job $FrontendJob -ErrorAction SilentlyContinue
    }
} finally {
    Write-Host "`nShutting down..." -ForegroundColor Yellow
    Stop-Job $BackendJob -ErrorAction SilentlyContinue
    Stop-Job $FrontendJob -ErrorAction SilentlyContinue
    Remove-Job $BackendJob -ErrorAction SilentlyContinue
    Remove-Job $FrontendJob -ErrorAction SilentlyContinue
    Write-Host "Done." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
}
