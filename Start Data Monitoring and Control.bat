@echo on
call %~dp0..\..\scripts\env.bat
cd %~dp0\source\usermonitor\webserver\
START "" python.exe start.py %*