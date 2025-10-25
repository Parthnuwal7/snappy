# Simple API Test Script for SNAPPY
Write-Host "=== SNAPPY API Tests ===" -ForegroundColor Cyan
Write-Host ""

# Test 1: Generate Keys
Write-Host "Test 1: Generate Product Keys" -ForegroundColor Yellow
$keysResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/admin/keys/generate" -Method POST -ContentType "application/json" -Body '{"count":3,"days":365}'
Write-Host "Keys generated:" -ForegroundColor Green
$keysResponse.keys | ForEach-Object { Write-Host "  - $_" }
Write-Host ""

# Save first key for next tests
$testKey = $keysResponse.keys[0]

# Test 2: Validate Key
Write-Host "Test 2: Validate Product Key" -ForegroundColor Yellow
Write-Host "Testing key: $testKey"
$validateResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/validate-key" -Method POST -ContentType "application/json" -Body "{`"key`":`"$testKey`"}"
Write-Host "Valid: $($validateResponse.valid)" -ForegroundColor Green
Write-Host ""

# Test 3: Register
Write-Host "Test 3: Register User" -ForegroundColor Yellow
$registerBody = @{
    email = "test@example.com"
    password = "testpass123"
    product_key = $testKey
} | ConvertTo-Json

try {
    $registerResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/register" -Method POST -ContentType "application/json" -Body $registerBody -SessionVariable websession
    Write-Host "User registered successfully!" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "User already exists (OK if running test again)" -ForegroundColor Yellow
    } else {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}
Write-Host ""

# Test 4: Login
Write-Host "Test 4: Login User" -ForegroundColor Yellow
$loginBody = @{
    email = "test@example.com"
    password = "testpass123"
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/login" -Method POST -ContentType "application/json" -Body $loginBody -SessionVariable websession
Write-Host "Login successful!" -ForegroundColor Green
Write-Host "User: $($loginResponse.user.email)" -ForegroundColor Green
Write-Host ""

# Test 5: Get Current User
Write-Host "Test 5: Get Current User (with session)" -ForegroundColor Yellow
$meResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/me" -Method GET -WebSession $websession
Write-Host "Current user: $($meResponse.user.email)" -ForegroundColor Green
Write-Host "Onboarded: $($meResponse.user.is_onboarded)" -ForegroundColor Green
Write-Host ""

# Test 6: Onboarding
Write-Host "Test 6: Complete Onboarding" -ForegroundColor Yellow
$onboardBody = @{
    firm_name = "Test Law Firm"
    firm_address = "123 Test Street, Test City - 110001"
    firm_email = "contact@testlawfirm.com"
    firm_phone = "+91-98765-43210"
    default_template = "LAW_001"
    invoice_prefix = "TEST"
    default_tax_rate = 18.0
    currency = "INR"
} | ConvertTo-Json

try {
    $onboardResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/onboard" -Method POST -ContentType "application/json" -Body $onboardBody -WebSession $websession
    Write-Host "Onboarding completed successfully!" -ForegroundColor Green
    Write-Host "Firm: $($onboardResponse.firm.firm_name)" -ForegroundColor Green
} catch {
    if ($_.Exception.Response.StatusCode.value__ -eq 400) {
        Write-Host "User already onboarded (OK if running test again)" -ForegroundColor Yellow
    } else {
        Write-Host "Error: $_" -ForegroundColor Red
    }
}
Write-Host ""

Write-Host "=== All Tests Complete ===" -ForegroundColor Cyan
