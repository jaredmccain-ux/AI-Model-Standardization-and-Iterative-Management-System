#!/bin/bash

# AI图像识别前端部署脚本
# 使用方法: ./deploy.sh

echo "=== AI图像识别前端部署脚本 ==="
echo "目标服务器: 114.55.52.100"
echo "开始部署..."

# 1. 安装依赖
echo "1. 安装项目依赖..."
npm install
if [ $? -ne 0 ]; then
    echo "错误: 依赖安装失败"
    exit 1
fi

# 2. 构建项目
echo "2. 构建前端项目..."
npm run build
if [ $? -ne 0 ]; then
    echo "错误: 项目构建失败"
    exit 1
fi

# 3. 检查构建结果
if [ ! -d "dist" ]; then
    echo "错误: 构建目录不存在"
    exit 1
fi

echo "3. 构建完成，生成文件:"
ls -la dist/

# 4. 构建Docker镜像
echo "4. 构建Docker镜像..."
docker build -t ai-frontend:latest .
if [ $? -ne 0 ]; then
    echo "错误: Docker镜像构建失败"
    exit 1
fi

echo "5. Docker镜像构建完成"
docker images | grep ai-frontend

echo "=== 部署准备完成 ==="
echo "接下来需要手动执行以下步骤:"
echo "1. 将Docker镜像推送到服务器或使用docker save/load传输"
echo "2. 在服务器上运行容器: docker run -d -p 80:80 --name ai-frontend ai-frontend:latest"
echo "3. 或者直接将dist目录内容上传到服务器的nginx目录"