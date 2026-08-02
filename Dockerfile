# MXReady 多阶段构建
# 阶段一：构建前端静态资源；阶段二：Python 3.11 运行时。
# 仅用于 MXReady 自身的演示/测试部署，不涉及远程 GPU 服务器的 Docker 编排。

# ---------- Stage 1: 前端构建 ----------
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- Stage 2: 运行时 ----------
FROM python:3.11-slim

# git 是扫描仓库的运行时依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY backend/ backend/
COPY runner/ runner/
COPY scripts/ scripts/
COPY rules/ rules/
COPY schemas/ schemas/
RUN pip install --no-cache-dir .

COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# 非 root 用户运行；预创建数据目录，保证命名卷首挂载时归属正确
RUN useradd --create-home mxready \
    && mkdir -p /app/data \
    && chown -R mxready:mxready /app
USER mxready

ENV MXREADY_DATA_DIR=/app/data \
    MXREADY_RULES_DIR=/app/rules/v1 \
    MXREADY_TEMP_DIR=/app/data/tmp \
    MXREADY_FRONTEND_DIR=/app/frontend/dist \
    MXREADY_LOG_LEVEL=INFO

EXPOSE 8000
CMD ["uvicorn", "mxready.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
