$base = "C:\Users\leobl\OneDrive\Documents\EtoroDemo"
$logDir = "$base\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

# Remove old DB for clean start
Remove-Item -Path "$base\etoro_portfolio.db" -ErrorAction SilentlyContinue

# Start backend
$backendJob = Start-Job -Name "etoro-backend" -ScriptBlock {
    param($dir)
    Set-Location $dir
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
} -ArgumentList $base

Write-Output "Backend started (Job ID: $($backendJob.Id))"
Start-Sleep -Seconds 5

# Verify backend
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Output "Backend health: $($r.StatusCode) - OK"
} catch {
    Write-Output "Backend health: FAILED - $_"
}

# Start frontend
$frontendJob = Start-Job -Name "etoro-frontend" -ScriptBlock {
    param($dir)
    Set-Location "$dir\frontend"
    npm run dev
} -ArgumentList $base

Write-Output "Frontend started (Job ID: $($frontendJob.Id))"
Start-Sleep -Seconds 8

# Verify frontend
try {
    $r = Invoke-WebRequest -Uri "http://localhost:5173" -UseBasicParsing -TimeoutSec 5
    Write-Output "Frontend: $($r.StatusCode) - OK"
} catch {
    Write-Output "Frontend: FAILED - $_"
}

# Verify portfolio API
try {
    $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/portfolio" -UseBasicParsing -TimeoutSec 5
    $data = $r | Select-Object -Expand Content | ConvertFrom-Json
    Write-Output "Portfolio API: $($r.StatusCode) - Value: `$$($data.total_value)"
} catch {
    Write-Output "Portfolio API: FAILED - $_"
}

Write-Output ""
Write-Output "=== Servers Running ==="
Write-Output "Frontend: http://localhost:5173"
Write-Output "Backend API: http://localhost:8000"
Write-Output "API Docs: http://localhost:8000/docs"
Write-Output "========================"
