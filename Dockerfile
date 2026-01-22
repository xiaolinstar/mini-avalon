# 使用官方 Python 运行时作为父镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=main:app

# 安装系统依赖 (如有需要，例如构建工具或数据库客户端)
# RUN apt-get update && apt-get install -y gcc default-libmysqlclient-dev && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令 (使用 gunicorn)
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "main:app"]
