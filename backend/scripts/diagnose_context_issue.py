"""
诊断脚本：检查为什么 ContextRetriever 没有工作
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

print("=" * 80)
print("🔍 诊断：ContextRetriever 问题")
print("=" * 80)

# 1. 检查修复是否存在
print("\n1️⃣ 检查代码修复")

import app.services.infrastructure.agents.runtime as runtime_module
import inspect

build_default_runtime_source = inspect.getsource(runtime_module.build_default_runtime)

if "context_retriever=context_retriever  # ✅ 修复" in build_default_runtime_source:
    print("✅ runtime.py 的修复代码存在")
else:
    print("❌ runtime.py 的修复代码不存在！")
    print("   问题：LoomAgentRuntime 创建时缺少 context_retriever 参数")

# 2. 检查 PlaceholderApplicationService
import app.services.application.placeholder.placeholder_service as placeholder_module

analyze_placeholder_source = inspect.getsource(placeholder_module.PlaceholderApplicationService.analyze_placeholder)

if "react_agent = self.agent_service" in analyze_placeholder_source:
    print("✅ placeholder_service.py 的修复代码存在")
else:
    print("❌ placeholder_service.py 的修复代码不存在！")
    print("   问题：仍在创建新的 AgentService，丢失了 context_retriever")

# 3. 检查 placeholders.py
import app.api.endpoints.placeholders as placeholders_module

get_or_create_context_retriever_source = inspect.getsource(
    placeholders_module.PlaceholderOrchestrationService._get_or_create_context_retriever
)

if "data_source.connection_config" in get_or_create_context_retriever_source:
    print("✅ placeholders.py 的修复代码存在")
else:
    print("❌ placeholders.py 的修复代码不存在！")
    print("   问题：使用了错误的字段名获取连接配置")

# 4. 测试完整流程
print("\n2️⃣ 测试 Loom Agent 是否支持 context_retriever")

from loom import agent as build_agent
import inspect

agent_sig = inspect.signature(build_agent)
params = list(agent_sig.parameters.keys())

if "context_retriever" in params:
    print(f"✅ Loom Agent 支持 context_retriever 参数")
    print(f"   参数位置: {params.index('context_retriever') + 1}/{len(params)}")
else:
    print(f"❌ Loom Agent 不支持 context_retriever 参数！")
    print(f"   可用参数: {', '.join(params[:10])}...")

# 5. 检查 Loom 版本
import loom
loom_version = getattr(loom, '__version__', 'unknown')
print(f"\n3️⃣ Loom 版本: {loom_version}")

if loom_version == "0.0.2":
    print("✅ Loom 版本正常")
else:
    print(f"⚠️ Loom 版本可能有变化: {loom_version}")

# 6. 总结
print("\n" + "=" * 80)
print("📊 诊断总结")
print("=" * 80)

print("""
如果所有检查都通过 (✅)，但 ContextRetriever 仍然没有工作，可能的原因：

1. 🔄 **服务没有重新加载代码**
   - 解决方案：重启后端服务
   - 命令：pkill -f uvicorn && uvicorn app.main:app --reload

2. 🐛 **Loom 框架没有调用 context_retriever**
   - 原因：Loom 0.0.2 的 context_retriever 可能需要特定配置
   - 解决方案：检查 Loom 文档或源代码

3. 🔀 **有其他代码路径绕过了修复**
   - 原因：可能有多个入口点
   - 解决方案：检查所有调用 AgentService 的地方

建议：在前端点击分析后，检查后端完整日志，搜索这些关键字：
  - "✅ 已启用 ContextRetriever 动态上下文机制"
  - "🔍 [SchemaContextRetriever.retrieve] 被调用"
  - "✅ [SchemaContextRetriever] 检索到"

如果这些日志都没有出现，说明 ContextRetriever 根本没有被 Loom 调用。
""")

print("=" * 80)
