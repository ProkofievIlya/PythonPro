@echo off

set /p a="Enter first number: "
set /p b="Enter second number: "

set /a sum=a+b
set /a difference=a-b
set /a multiplication=a*b

echo.
echo Sum: %sum%
echo Difference: %difference%
echo Multiplication: %multiplication%

pause