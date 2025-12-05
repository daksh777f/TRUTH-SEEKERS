# Test Backend API
Write-Host "Testing Verique Backend..." -ForegroundColor Cyan

# Test 1: Health Check
Write-Host "`n1. Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method GET
    Write-Host "✓ Health check passed" -ForegroundColor Green
    Write-Host "  Status: $($health.status)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Health check failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Verify Endpoint
Write-Host "`n2. Testing verify endpoint..." -ForegroundColor Yellow
$body = @{
    text = "The sky is blue."
    vertical = "general"
} | ConvertTo-Json

try {
    $result = Invoke-RestMethod -Uri "http://127.0.0.1:8000/v1/verify" -Method POST -Body $body -ContentType "application/json"
    Write-Host "✓ Verification endpoint works!" -ForegroundColor Green
    Write-Host "  Page Score: $($result.page_score)" -ForegroundColor Gray
    Write-Host "  Claims Found: $($result.claims.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Verification failed: $_" -ForegroundColor Red
    Write-Host "  Error details: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`nTest complete!" -ForegroundColor Cyan
