@echo off
echo ========================================
echo SNAPPY Authentication API Tests
echo ========================================
echo.

echo [1/4] Testing: Generate Product Keys
echo.
curl -X POST http://localhost:5000/api/auth/admin/keys/generate -H "Content-Type: application/json" -d "{\"count\": 3, \"days\": 365}"
echo.
echo.

echo ========================================
echo [2/4] Testing: Validate Product Key
echo Copy one of the keys from above and test validation
echo.
set /p PRODUCT_KEY="Enter a product key to test (or press Enter to skip): "
if not "%PRODUCT_KEY%"=="" (
    curl -X POST http://localhost:5000/api/auth/validate-key -H "Content-Type: application/json" -d "{\"key\": \"%PRODUCT_KEY%\"}"
    echo.
    echo.
)

echo ========================================
echo [3/4] Testing: User Registration
echo.
curl -X POST http://localhost:5000/api/auth/register -H "Content-Type: application/json" -d "{\"email\": \"test@example.com\", \"password\": \"testpass123\", \"product_key\": \"%PRODUCT_KEY%\"}"
echo.
echo.

echo ========================================
echo [4/4] Testing: User Login
echo.
curl -X POST http://localhost:5000/api/auth/login -H "Content-Type: application/json" -c cookies.txt -d "{\"email\": \"test@example.com\", \"password\": \"testpass123\"}"
echo.
echo.

echo ========================================
echo [BONUS] Testing: Get Current User
echo.
curl -X GET http://localhost:5000/api/auth/me -b cookies.txt
echo.
echo.

echo ========================================
echo Tests Complete!
echo ========================================
pause
