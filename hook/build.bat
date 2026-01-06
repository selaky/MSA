@echo off
chcp 65001 >nul
setlocal

echo ========================================
echo    MSA Hook 模块构建脚本
echo ========================================
echo.

cd /d "%~dp0"

:: 检查 CMake 是否可用
where cmake >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 CMake，请先安装 CMake 并添加到 PATH
    pause
    exit /b 1
)

:: 创建构建目录
if not exist build mkdir build
cd build

:: 配置项目（不指定生成器，让 CMake 自动检测）
echo [信息] 正在配置项目...
cmake .. -DCMAKE_BUILD_TYPE=Release
if %errorlevel% neq 0 (
    echo [错误] CMake 配置失败
    pause
    exit /b 1
)

:: 构建项目
echo.
echo [信息] 正在构建项目...
cmake --build . --config Release
if %errorlevel% neq 0 (
    echo [错误] 构建失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo    构建完成！
echo ========================================
echo.
echo 输出文件位于: %cd%\bin\Release\
echo   - msa_hook.dll    : Hook DLL
echo   - click_test.exe  : 测试程序
echo.
echo 使用方法:
echo   1. 启动游戏
echo   2. 双击运行 click_test.exe
echo   3. 按提示进行测试
echo.

pause
