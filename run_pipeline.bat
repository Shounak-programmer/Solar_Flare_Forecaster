@echo off
REM =====================================================================
REM  Solar Flare Detection System - L1 - end-to-end pipeline runner
REM
REM  Usage:  run_pipeline.bat [mode]
REM
REM    setup       install Python dependencies (requirements.txt)
REM    serve       launch the dashboard web server            (DEFAULT)
REM    dashboard   rebuild dashboard_data JSON only            (~1 min)
REM    eval        refresh evaluation sidecars + dashboard     (~5-10 min)
REM    forecast    rebuild forecast features + eval + dashboard
REM    detect      rerun the 5-detector detection + catalogs   (slow, ~1-3 h)
REM    analysis    detect + forecast + dashboard (full reproduce from parquet)
REM    tft         train the TFT (needs a CUDA GPU, ~50 min)
REM    data        build light curves + labels from RAW FITS   (needs archives)
REM    full        data + analysis + tft + dashboard
REM
REM  Stages from the committed processed parquet (detect/forecast/eval/
REM  dashboard) reproduce all results WITHOUT the 365 GB of raw FITS.
REM  "data" and "full" require the raw archives (paths via src/config.py).
REM =====================================================================
setlocal
cd /d "%~dp0"
title Aditya-L1 pipeline runner

REM --- pick a Python launcher (python, else py) ---
set "PY=python"
where python >nul 2>nul || set "PY=py"
%PY% --version >nul 2>nul
if errorlevel 1 (echo [ERROR] Python 3.10+ not found on PATH. & pause & exit /b 1)

set "MODE=%~1"
if "%MODE%"=="" set "MODE=serve"
echo === Aditya-L1 pipeline runner === mode: %MODE%

if /i "%MODE%"=="setup"     goto :setup
if /i "%MODE%"=="serve"     goto :serve
if /i "%MODE%"=="dashboard" goto :m_dashboard
if /i "%MODE%"=="eval"      goto :m_eval
if /i "%MODE%"=="forecast"  goto :m_forecast
if /i "%MODE%"=="detect"    goto :m_detect
if /i "%MODE%"=="analysis"  goto :m_analysis
if /i "%MODE%"=="tft"       goto :m_tft
if /i "%MODE%"=="data"      goto :m_data
if /i "%MODE%"=="full"      goto :m_full
echo [ERROR] Unknown mode "%MODE%".
echo         Use: setup ^| serve ^| dashboard ^| eval ^| forecast ^| detect ^| analysis ^| tft ^| data ^| full
exit /b 1

REM ------------------------------- modes -------------------------------
:setup
echo. & echo [setup] Installing dependencies ...
%PY% -m pip install -r requirements.txt || goto :fail
echo [OK] dependencies installed.
goto :done

:serve
if not exist "dashboard_data\manifest.json" ( call :do_dashboard || goto :fail )
echo. & echo Starting dashboard on http://127.0.0.1:8000  (Ctrl+C to stop)
start "" /min cmd /c "timeout /t 3 >nul & start "" http://127.0.0.1:8000"
%PY% -m uvicorn app.dashboard_server:app --host 127.0.0.1 --port 8000
goto :done

:m_dashboard
call :do_dashboard || goto :fail
goto :done

:m_eval
call :do_eval      || goto :fail
call :do_dashboard || goto :fail
goto :done

:m_forecast
call :do_forecast  || goto :fail
call :do_dashboard || goto :fail
goto :done

:m_detect
call :do_detect    || goto :fail
goto :done

:m_analysis
call :do_detect    || goto :fail
call :do_forecast  || goto :fail
call :do_dashboard || goto :fail
goto :done

:m_tft
call :do_tft       || goto :fail
goto :done

:m_data
call :do_data      || goto :fail
goto :done

:m_full
call :do_data      || goto :fail
call :do_detect    || goto :fail
call :do_forecast  || goto :fail
call :do_tft       || goto :fail
call :do_dashboard || goto :fail
goto :done

REM --------------------------- subroutines -----------------------------
:do_data
echo. & echo === DATA (Phase 1-2): build light curves + labels (requires RAW FITS) ===
%PY% scripts\01_build_daily_lightcurves.py || exit /b 1
%PY% scripts\05_standardize_auxiliary.py   || exit /b 1
%PY% scripts\06_build_labeled_dataset.py   || exit /b 1
echo [OK] data build complete.
exit /b 0

:do_detect
echo. & echo === DETECTION (Phase 3): tune -^> detect -^> fuse -^> qpp -^> evaluate ===
%PY% scripts\10_tune_thresholds.py          || exit /b 1
%PY% scripts\09_detect_per_detector.py --build-all || exit /b 1
%PY% scripts\11_build_master_catalog.py     || exit /b 1
%PY% scripts\12_detect_qpps.py              || exit /b 1
%PY% scripts\gate3_evaluate.py              || exit /b 1
%PY% scripts\13_evaluate.py                 || exit /b 1
echo [OK] detection complete (master catalog + sidecars refreshed).
exit /b 0

:do_forecast
echo. & echo === FORECASTING (Phase 4): features -^> baselines -^> calibrate ===
%PY% scripts\14_build_forecast_features.py  || exit /b 1
%PY% scripts\16_baselines.py                || exit /b 1
%PY% scripts\18_calibrate_evaluate.py       || exit /b 1
echo [OK] forecasting complete (forecasting_metrics refreshed).
exit /b 0

:do_eval
echo. & echo === EVAL refresh: detection + forecasting metric sidecars ===
%PY% scripts\gate3_evaluate.py              || exit /b 1
%PY% scripts\13_evaluate.py                 || exit /b 1
%PY% scripts\16_baselines.py                || exit /b 1
%PY% scripts\18_calibrate_evaluate.py       || exit /b 1
echo [OK] evaluation sidecars refreshed.
exit /b 0

:do_tft
echo. & echo === TFT (Phase 4c): single time-boxed run (needs CUDA GPU, ~50 min) ===
%PY% scripts\17_train_tft.py                || exit /b 1
echo [OK] TFT trained (tft_metrics.json refreshed).
exit /b 0

:do_dashboard
echo. & echo === DASHBOARD: export pre-computed JSON ===
%PY% scripts\dashboard\export_dashboard_data.py || exit /b 1
%PY% scripts\dashboard\export_wavelets.py       || exit /b 1
echo [OK] dashboard_data refreshed.
exit /b 0

REM ----------------------------- endings -------------------------------
:fail
echo.
echo [FAILED] A stage reported an error (see the message above). Pipeline stopped.
pause
exit /b 1

:done
echo.
echo [DONE] mode "%MODE%" finished.
if /i not "%MODE%"=="serve" pause
exit /b 0
