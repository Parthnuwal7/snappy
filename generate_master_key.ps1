# Generate Master Key
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/auth/admin/keys/generate" -Method POST -ContentType "application/json" -Body '{"count":1,"days":3650}'
Write-Host "=== MASTER KEY FOR SNAPPY ===" -ForegroundColor Green
Write-Host ""
Write-Host "Product Key: $($response.keys[0])" -ForegroundColor Yellow
Write-Host "Valid for: 10 years" -ForegroundColor Cyan
Write-Host ""
Write-Host "Test Credentials:" -ForegroundColor Green
Write-Host "Email: admin@snappy.local" -ForegroundColor Yellow
Write-Host "Password: Admin@123" -ForegroundColor Yellow
Write-Host ""
