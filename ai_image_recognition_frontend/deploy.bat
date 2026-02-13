@echo off
chcp 65001 >nul
echo === AI图像识别前端部署脚本 ===
echo 目标服务器: 114.55.52.100
echo 开始部署...
echo.

REM 1. 安装依赖
echo 1. 安装项目依赖...
npm install
if %errorlevel% neq 0 (
    echo 错误: 依赖安装失败
    pause
    exit /b 1
)

REM 2. 构建项目
echo 2. 构建前端项目...
npm run build
if %errorlevel% neq 0 (
    echo 错误: 项目构建失败
    pause
    exit /b 1
)

REM 3. 检查构建结果
if not exist "dist" (
    echo 错误: 构建目录不存在
    pause
    exit /b 1
)

echo 3. 构建完成，生成文件:
dir dist

REM 4. 构建Docker镜像
echo 4. 构建Docker镜像...
docker build -t ai-frontend:latest .
if %errorlevel% neq 0 (
    echo 错误: Docker镜像构建失败
    pause
    exit /b 1
)

echo 5. Docker镜像构建完成
docker images | findstr ai-frontend

echo.
echo === 部署准备完成 ===
echo 接下来需要手动执行以下步骤:
echo 1. 将Docker镜像推送到服务器或使用docker save/load传输
echo 2. 在服务器上运行容器: docker run -d -p 80:80 --name ai-frontend ai-frontend:latest
echo 3. 或者直接将dist目录内容上传到服务器的nginx目录
echo.
pause