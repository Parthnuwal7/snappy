# SNAPPY Authentication API Tests (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SNAPPY Authentication API Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Generate Product Keys
Write-Host "[1/4] Testing: Generate Product Keys" -ForegroundColor Yellow
Write-Host ""
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/admin/keys/generate" `
        -Method POST `
        -ContentType "application/json" `
        -Body (@{count=3; days=365} | ConvertTo-Json)
    
    Write-Host "[SUCCESS]" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
    $productKey = $response.keys[0]
    Write-Host ""
} catch {
    Write-Host "[ERROR] $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

# Test 2: Validate Product Key
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[2/4] Testing: Validate Product Key" -ForegroundColor Yellow
Write-Host "Using key: $productKey"
Write-Host ""
try {
    $response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/validate-key" `
        -Method POST `
        -ContentType "application/json" `
        -Body (@{key=$productKey} | ConvertTo-Json)
    
    Write-Host "Success!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
    Write-Host ""
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

# Test 3: User Registration
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[3/4] Testing: User Registration" -ForegroundColor Yellow
Write-Host ""
try {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/register" `
        -Method POST `
        -ContentType "application/json" `
        -Body (@{email="test@example.com"; password="testpass123"; product_key=$productKey} | ConvertTo-Json) `
        -SessionVariable session `
        -ErrorAction SilentlyContinue
    
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
    Write-Host ""
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "⚠ User already exists (this is expected if you ran the test before)" -ForegroundColor Yellow
    } else {
        Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# Test 4: User Login
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[4/4] Testing: User Login" -ForegroundColor Yellow
Write-Host ""
try {
    $session = New-Object Microsoft.PowerShell.Commands.WebRequestSession
    $response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body (@{email="test@example.com"; password="testpass123"} | ConvertTo-Json) `
        -WebSession $session
    
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host ($response | ConvertTo-Json -Depth 10)
    Write-Host ""
    
    # Test 5: Get Current User
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[BONUS] Testing: Get Current User (with session)" -ForegroundColor Yellow
    Write-Host ""
    
    $userResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/me" `
        -Method GET `
        -WebSession $session
    
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host ($userResponse | ConvertTo-Json -Depth 10)
    Write-Host ""
    
    # Test 6: Onboarding
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "[BONUS] Testing: Complete Onboarding" -ForegroundColor Yellow
    Write-Host ""
    
    $firmData = @{
        firm_name = "Test Law Firm"
        firm_address = "123 Test Street, Test City"
        firm_email = "contact@testlawfirm.com"
        firm_phone = "+91-98765-43210"
        default_template = "LAW_001"
        invoice_prefix = "TEST"
        default_tax_rate = 18.0
        currency = "INR"
    }
    
    $onboardResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/onboard" `
        -Method POST `
        -ContentType "application/json" `
        -Body ($firmData | ConvertTo-Json) `
        -WebSession $session
    
    Write-Host "✓ Success!" -ForegroundColor Green
    Write-Host ($onboardResponse | ConvertTo-Json -Depth 10)
    Write-Host ""
    
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Tests Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
