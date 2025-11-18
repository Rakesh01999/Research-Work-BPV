@echo off
echo ========================================
echo SUMO Simulation with Vehicle Data Output
echo ========================================

echo.
echo 1. Starting SUMO Simulation...
echo    - Collecting vehicle speed data
echo    - Collecting position data  
echo    - Collecting battery data
echo    - Collecting charging station data
echo.

sumo -c Test1.sumocfg

echo.
echo 2. Simulation Complete! Generated files:
echo    - fcd.xml (vehicle positions, speeds)
echo    - tripinfo.xml (trip summaries)
echo    - battery.xml (battery levels)
echo    - chargingstations.xml (charging data)
echo.

echo 3. Analyzing data...
python vehicle_monitor.py

echo.
echo ========================================
echo Press any key to exit...
pause