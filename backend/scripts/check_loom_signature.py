"""检查Loom Agent的参数签名"""
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import inspect
import loom

# 检查 agent 函数的签名
sig = inspect.signature(loom.agent)

print("🔍 Loom Agent 函数参数列表:\n")
for name, param in sig.parameters.items():
    annotation = param.annotation if param.annotation != inspect.Parameter.empty else "Any"
    default = f" = {param.default}" if param.default != inspect.Parameter.empty else ""
    print(f"  • {name}: {annotation}{default}")

# 检查是否有 context_retriever 参数
if 'context_retriever' in sig.parameters:
    print("\n✅ Loom Agent 支持 context_retriever 参数")
else:
    print("\n❌ Loom Agent 不支持 context_retriever 参数")
    print("⚠️  这可能是问题的根源！")

# 检查 Agent 类
print("\n🔍 检查 loom.Agent 类...")
try:
    agent_class = loom.Agent
    print(f"Agent 类: {agent_class}")
    init_sig = inspect.signature(agent_class.__init__)
    print("\nAgent.__init__ 参数:")
    for name, param in init_sig.parameters.items():
        if name == 'self':
            continue
        annotation = param.annotation if param.annotation != inspect.Parameter.empty else "Any"
        default = f" = {param.default}" if param.default != inspect.Parameter.empty else ""
        print(f"  • {name}: {annotation}{default}")

    if 'context_retriever' in init_sig.parameters:
        print("\n✅ Agent.__init__ 支持 context_retriever 参数")
    else:
        print("\n❌ Agent.__init__ 不支持 context_retriever 参数")
except Exception as e:
    print(f"无法检查 Agent 类: {e}")
