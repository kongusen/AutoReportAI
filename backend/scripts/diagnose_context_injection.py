#!/usr/bin/env python3
"""
诊断 Context 注入位置和结构

目标：
1. 验证 Context Retriever 的 inject_as 参数
2. 跟踪 Context 注入到 System Message 还是 User Message
3. 检查最终发送给 LLM 的 Messages 结构
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))


def check_context_retriever_config():
    """检查 Context Retriever 配置"""
    print("\n" + "=" * 80)
    print("🔍 检查 Context Retriever 配置")
    print("=" * 80)

    try:
        # 检查 placeholders.py 中是否有 context_retriever 初始化
        placeholders_file = backend_path / "app/api/endpoints/placeholders.py"

        if placeholders_file.exists():
            content = placeholders_file.read_text()

            # 检查是否创建了 context_retriever
            if "ContextRetriever(" in content:
                print("✅ 发现 ContextRetriever 实例化代码")

                # 查找 inject_as 参数
                import re
                inject_as_matches = re.findall(r'inject_as\s*=\s*["\'](\w+)["\']', content)
                if inject_as_matches:
                    print(f"✅ inject_as 参数: {inject_as_matches}")
                    for value in inject_as_matches:
                        if value == "system":
                            print("   ✅ 正确：Context 将注入到 System Message")
                        else:
                            print(f"   ⚠️ 注意：Context 将注入到 {value}")
                else:
                    print("⚠️ 未找到 inject_as 参数，使用默认值")

                # 查找 top_k 参数
                top_k_matches = re.findall(r'top_k\s*=\s*(\d+)', content)
                if top_k_matches:
                    print(f"✅ top_k 参数: {top_k_matches}")

            else:
                print("❌ 未找到 ContextRetriever 实例化代码")
                print("   这意味着 Dynamic Context 未被启用！")
                print(f"\n💡 建议：在 {placeholders_file} 中添加 Context Retriever")

        else:
            print(f"❌ 文件不存在: {placeholders_file}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


def check_context_format():
    """检查 Context 格式化代码"""
    print("\n" + "=" * 80)
    print("🔍 检查 Context 格式化代码")
    print("=" * 80)

    try:
        context_file = backend_path / "app/services/infrastructure/agents/context_retriever.py"

        if context_file.exists():
            content = context_file.read_text()

            # 检查 format_documents 方法
            if "def format_documents" in content:
                print("✅ 发现 format_documents 方法")

                # 检查是否有强化的约束说明
                if "⚠️⚠️⚠️" in content and "关键约束" in content:
                    print("✅ 已包含强化的约束说明")
                else:
                    print("⚠️ Context 格式可能需要优化")

                # 检查是否说明了违反后果
                if "违反此约束将导致" in content or "违反" in content:
                    print("✅ 已说明违反约束的后果")
                else:
                    print("⚠️ 建议添加违反约束的后果说明")

            else:
                print("❌ 未找到 format_documents 方法")

        else:
            print(f"❌ 文件不存在: {context_file}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")


def check_facade_prompt_composition():
    """检查 Facade 的 Prompt 组装逻辑"""
    print("\n" + "=" * 80)
    print("🔍 检查 Facade Prompt 组装逻辑")
    print("=" * 80)

    try:
        facade_file = backend_path / "app/services/infrastructure/agents/facade.py"

        if facade_file.exists():
            content = facade_file.read_text()

            # 检查 _compose_prompt 方法
            if "def _compose_prompt" in content:
                print("✅ 发现 _compose_prompt 方法")

                # 检查 context 是否被转为 JSON
                if "json.dumps(request.context" in content:
                    print("✅ Static Context 被转为 JSON 并添加到 User Prompt")

                # 检查 sections 的组装顺序
                import re
                sections_match = re.search(
                    r'sections\s*=\s*\[(.*?)\]',
                    content,
                    re.DOTALL
                )
                if sections_match:
                    sections_str = sections_match.group(1)
                    print("\n📋 User Prompt 的组装顺序:")

                    # 提取每个 section
                    section_lines = [line.strip() for line in sections_str.split('\n') if line.strip() and not line.strip().startswith('#')]
                    for i, line in enumerate(section_lines, 1):
                        # 简化显示
                        if '###' in line:
                            section_name = line.split('###')[1].split('\\n')[0].strip()
                            print(f"   {i}. {section_name}")

                    # 检查 context 的位置
                    context_line_idx = None
                    for i, line in enumerate(section_lines):
                        if 'context' in line.lower():
                            context_line_idx = i
                            break

                    if context_line_idx is not None:
                        if context_line_idx >= len(section_lines) - 2:
                            print(f"\n⚠️ Static Context 位于 User Prompt 末尾（第 {context_line_idx + 1} 部分）")
                            print("   这可能导致 LLM 优先关注其他信息")
                        else:
                            print(f"\n✅ Static Context 位于第 {context_line_idx + 1} 部分")

            else:
                print("❌ 未找到 _compose_prompt 方法")

        else:
            print(f"❌ 文件不存在: {facade_file}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()


def check_runtime_context_retriever():
    """检查 Runtime 的 Context Retriever 配置"""
    print("\n" + "=" * 80)
    print("🔍 检查 Runtime Context Retriever 配置")
    print("=" * 80)

    try:
        runtime_file = backend_path / "app/services/infrastructure/agents/runtime.py"

        if runtime_file.exists():
            content = runtime_file.read_text()

            # 检查 build_default_runtime 是否接收 context_retriever
            if "context_retriever: Optional[Any] = None" in content:
                print("✅ build_default_runtime 接收 context_retriever 参数")

            # 检查是否传递给 _create_agent
            if 'context_retriever=context_retriever' in content:
                print("✅ context_retriever 被传递给 _create_agent")

            # 检查是否添加到 agent_kwargs
            if 'agent_kwargs["context_retriever"] = context_retriever' in content:
                print("✅ context_retriever 被添加到 agent_kwargs")

                # 检查日志
                if "已启用 ContextRetriever 动态上下文机制" in content:
                    print("✅ 包含启用 ContextRetriever 的日志")

        else:
            print(f"❌ 文件不存在: {runtime_file}")

    except Exception as e:
        print(f"❌ 检查失败: {e}")


def generate_diagnostic_report():
    """生成诊断报告"""
    print("\n" + "=" * 80)
    print("📊 Context 工程诊断报告")
    print("=" * 80)

    report_lines = [
        "",
        "## 诊断结果",
        "",
        "### 1. Context Retriever 配置",
        ""
    ]

    # 检查文件是否存在
    files_to_check = [
        ("placeholders.py", backend_path / "app/api/endpoints/placeholders.py"),
        ("context_retriever.py", backend_path / "app/services/infrastructure/agents/context_retriever.py"),
        ("facade.py", backend_path / "app/services/infrastructure/agents/facade.py"),
        ("runtime.py", backend_path / "app/services/infrastructure/agents/runtime.py"),
    ]

    all_exist = True
    for name, path in files_to_check:
        if path.exists():
            report_lines.append(f"✅ {name} 存在")
        else:
            report_lines.append(f"❌ {name} 不存在")
            all_exist = False

    report_lines.extend([
        "",
        "### 2. 关键发现",
        "",
        "根据上述检查，以下是需要注意的要点：",
        ""
    ])

    # 读取 placeholders.py
    placeholders_file = backend_path / "app/api/endpoints/placeholders.py"
    if placeholders_file.exists():
        content = placeholders_file.read_text()
        if "ContextRetriever(" not in content:
            report_lines.extend([
                "❌ **关键问题**：placeholders.py 中未创建 ContextRetriever 实例",
                "   - 这意味着 Dynamic Context（Schema）未被启用",
                "   - Agent 只能依赖 Static Context（JSON）",
                "   - 建议：参考 CONTEXT_OPTIMIZATION_IMPLEMENTATION.md 启用 Context Retriever",
                ""
            ])
        else:
            report_lines.extend([
                "✅ placeholders.py 中已创建 ContextRetriever 实例",
                "   - Dynamic Context 已启用",
                "   - 需要验证 inject_as 参数是否为 'system'",
                ""
            ])

    report_lines.extend([
        "",
        "### 3. 建议的优化步骤",
        "",
        "1. **立即执行**：启用 Context Retriever（如果未启用）",
        "2. **验证配置**：确保 inject_as='system'",
        "3. **优化格式**：强化 Schema Context 的约束说明（已完成）",
        "4. **添加日志**：在关键位置添加日志，跟踪 Context 流转",
        ""
    ])

    # 写入报告
    report_file = backend_path / "docs/CONTEXT_DIAGNOSTIC_REPORT.md"
    report_file.write_text("\n".join(report_lines))

    print("\n" + "=" * 80)
    print(f"📄 诊断报告已生成: {report_file}")
    print("=" * 80)


def main():
    """主函数"""
    print("\n" + "=" * 80)
    print("🔧 Context 工程诊断工具")
    print("=" * 80)
    print("\n这个工具将帮助你诊断 Context 的传递和注入情况\n")

    # 执行各项检查
    check_context_retriever_config()
    check_context_format()
    check_facade_prompt_composition()
    check_runtime_context_retriever()

    # 生成报告
    generate_diagnostic_report()

    print("\n" + "=" * 80)
    print("✅ 诊断完成！")
    print("=" * 80)
    print("\n📖 请查看生成的报告了解详情")
    print("📁 报告位置: backend/docs/CONTEXT_DIAGNOSTIC_REPORT.md")
    print()


if __name__ == "__main__":
    main()
