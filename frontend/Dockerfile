# ============================================================
# 前端镜像（Vue3 构建 → Nginx 静态托管 + /api 反代）
# 构建上下文：frontend 目录
# ============================================================
# ---- 构建阶段 ----
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --registry=https://registry.npmmirror.com
COPY . .
RUN npm run build

# ---- 运行阶段 ----
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
