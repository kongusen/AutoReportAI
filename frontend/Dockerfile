# ==========================================
# AutoReportAI Frontend Dockerfile
# React Agent Architecture - Next.js 14 + TypeScript
# 支持React Agent智能UI和实时WebSocket通信
# ==========================================

# ==========================================
# 基础Node.js镜像
# ==========================================
FROM node:18-alpine AS base

# 安装系统依赖
RUN apk add --no-cache \
    libc6-compat \
    curl \
    dumb-init

# 设置工作目录
WORKDIR /app

# 优化npm配置
RUN npm config set registry https://registry.npmjs.org/ && \
    npm config set audit-level high && \
    npm config set fund false

# ==========================================
# 依赖安装阶段
# ==========================================
FROM base AS deps

# 复制包管理文件
COPY package.json package-lock.json* ./

# 安装生产依赖
RUN npm ci --only=production && npm cache clean --force

# ==========================================
# 开发依赖安装阶段
# ==========================================
FROM base AS dev-deps

# 复制包管理文件
COPY package.json package-lock.json* ./

# 安装所有依赖（包括开发依赖）
RUN npm ci && npm cache clean --force

# ==========================================
# 开发环境构建 - React Agent UI开发模式
# ==========================================
FROM base AS development

# 复制开发依赖
COPY --from=dev-deps /app/node_modules ./node_modules

# 复制源代码
COPY . .

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 创建.next目录并设置权限
RUN mkdir -p /app/.next && \
    chown -R nextjs:nodejs /app && \
    chmod 755 /app/.next

# React Agent开发环境配置
ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1 \
    CHOKIDAR_USEPOLLING=true \
    WATCHPACK_POLLING=true \
    FORCE_COLOR=1 \
    NODE_OPTIONS="--max-old-space-size=4096"

# 切换用户  
USER nextjs

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# 使用dumb-init作为PID 1，优化信号处理
ENTRYPOINT ["dumb-init", "--"]
CMD ["npm", "run", "dev"]

# ==========================================
# 构建阶段
# ==========================================
FROM base AS builder

# 复制开发依赖
COPY --from=dev-deps /app/node_modules ./node_modules

# 复制源代码
COPY . .

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL
ENV NODE_ENV=$NODE_ENV
ENV NEXT_TELEMETRY_DISABLED=1

# TypeScript 类型检查
RUN npm run type-check

# 构建应用
RUN npm run build

# ==========================================
# 生产运行阶段 - React Agent UI生产环境
# ==========================================
FROM base AS production

# 设置生产环境变量
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0" \
    NODE_OPTIONS="--max-old-space-size=2048"

# 创建非root用户
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制生产依赖
COPY --from=deps --chown=nextjs:nodejs /app/node_modules ./node_modules

# 复制构建产物
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# 复制静态资源
COPY --from=builder --chown=nextjs:nodejs /app/public ./public

# 创建临时目录用于React Agent UI缓存
RUN mkdir -p /app/.next/cache && \
    chown -R nextjs:nodejs /app/.next/cache

# 切换到非root用户
USER nextjs

# 暴露端口
EXPOSE 3000

# 健康检查 - 针对React Agent UI优化
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# 使用dumb-init优化生产环境信号处理
ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "server.js"]