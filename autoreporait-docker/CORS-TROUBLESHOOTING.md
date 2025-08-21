# CORS 跨域问题解决指南

## 🚨 问题描述
当前端部署在服务器上时，访问后端API可能遇到CORS (Cross-Origin Resource Sharing) 跨域错误。

## 🔍 问题诊断

### 1. 运行诊断脚本
```bash
cd autoreporait-docker
./diagnose-cors.sh
```

### 2. 查看浏览器错误
打开浏览器开发者工具 (F12)，查看Console中是否有类似错误：
```
Access to XMLHttpRequest at 'http://server-ip:8000/api/v1/...' 
from origin 'http://server-ip:3000' has been blocked by CORS policy
```

## ⚙️ 解决方案

### 方案1: 明确指定允许的来源（推荐）

编辑 `.env` 文件：

```bash
# 本地开发
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# 服务器部署（替换为您的实际IP）
CORS_ORIGINS=http://localhost:3000,http://your-server-ip:3000

# 多个来源
CORS_ORIGINS=http://localhost:3000,http://192.168.1.100:3000,https://your-domain.com
```

### 方案2: 使用正则表达式（更灵活）

```bash
# 允许任何端口的localhost和127.0.0.1
CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1)(:\d+)?$

# 允许特定IP的任何端口
CORS_ORIGIN_REGEX=^https?://(localhost|127\.0\.0\.1|192\.168\.1\.100)(:\d+)?$

# 允许特定域名的所有子域
CORS_ORIGIN_REGEX=^https?://.*\.yourdomain\.com$
```

### 方案3: 临时允许所有来源（仅用于测试）

```bash
# ⚠️ 不安全，仅用于开发测试
CORS_ORIGINS=*
```

## 🛠️ 常见部署场景

### 内网部署
```bash
# 替换为您的服务器内网IP
CORS_ORIGINS=http://192.168.1.100:3000,http://10.0.0.100:3000
```

### 云服务器部署
```bash
# 替换为您的公网IP或域名
CORS_ORIGINS=http://your-public-ip:3000,https://your-domain.com
```

### Nginx代理部署
```bash
# 如果前端通过Nginx代理
CORS_ORIGINS=https://your-domain.com,http://your-domain.com
```

## 🔄 应用配置更改

修改配置后，重启容器：

```bash
# 停止容器
docker-compose down

# 重新构建并启动
docker-compose up -d

# 查看启动日志，确认CORS配置
docker-compose logs backend | grep CORS
```

## 🧪 测试CORS配置

### 使用curl测试
```bash
curl -H "Origin: http://your-frontend-url" \
     -H "Access-Control-Request-Method: POST" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://your-server:8000/api/v1/health
```

### 浏览器测试
1. 打开浏览器开发者工具 (F12)
2. 访问前端页面
3. 尝试登录或调用API
4. 检查Network标签页中的请求头和响应头

## 📋 配置文件说明

### 开发环境 (.env)
适用于本地开发和测试

### 生产环境 (.env.production.example)
复制为 `.env.production` 并修改：
```bash
cp .env.production.example .env.production
# 编辑 .env.production 文件
```

## 🔒 安全建议

1. **生产环境**: 明确指定允许的域名，避免使用通配符 `*`
2. **HTTPS**: 生产环境建议使用HTTPS
3. **定期检查**: 定期检查和更新CORS配置
4. **最小权限**: 只允许必需的HTTP方法和头部

## 🆘 常见错误及解决

### 错误1: "CORS policy: No 'Access-Control-Allow-Origin' header"
**解决**: 检查CORS_ORIGINS配置是否包含前端URL

### 错误2: "CORS policy: The request client is not a secure context"
**解决**: 混合使用HTTP和HTTPS，确保协议一致

### 错误3: 配置不生效
**解决**: 确保重启了容器，检查环境变量是否正确加载

## 📞 获取帮助

如果仍有问题，请提供以下信息：
1. 服务器IP地址
2. 前端访问URL
3. 浏览器错误信息
4. `./diagnose-cors.sh` 的输出结果