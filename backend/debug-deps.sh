#!/bin/bash
# 调试依赖问题的脚本

echo "🔍 调试各容器的依赖状态..."

echo "📦 检查后端容器依赖:"
docker-compose exec backend python -c "
try:
    import unidecode, croniter, fastapi_limiter
    print('✅ 后端容器: 所有关键依赖都存在')
    print(f'  unidecode: {unidecode.__version__}')
    print(f'  croniter: {croniter.__version__}')
except ImportError as e:
    print(f'❌ 后端容器缺少依赖: {e}')
" 2>/dev/null || echo "❌ 后端容器无法连接"

echo ""
echo "📦 检查Worker容器依赖:"
docker-compose exec celery-worker python -c "
try:
    import unidecode, croniter, fastapi_limiter
    print('✅ Worker容器: 所有关键依赖都存在')
    print(f'  unidecode: {unidecode.__version__}')
    print(f'  croniter: {croniter.__version__}')
except ImportError as e:
    print(f'❌ Worker容器缺少依赖: {e}')
" 2>/dev/null || echo "❌ Worker容器无法连接"

echo ""
echo "📦 检查Beat容器依赖:"
docker-compose exec celery-beat python -c "
try:
    import unidecode, croniter, fastapi_limiter
    print('✅ Beat容器: 所有关键依赖都存在')
    print(f'  unidecode: {unidecode.__version__}')
    print(f'  croniter: {croniter.__version__}')
except ImportError as e:
    print(f'❌ Beat容器缺少依赖: {e}')
" 2>/dev/null || echo "❌ Beat容器无法连接"

echo ""
echo "🏗️  检查镜像构建时间:"
docker images | grep "autorport-dev"