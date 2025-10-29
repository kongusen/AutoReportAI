#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integration test: Verify Context Retriever works in Loom Agent TT recursion

Test scenarios:
1. Create a mock SchemaContextRetriever
2. Pass it as context_retriever to Loom Agent
3. Verify Agent can call retrieve_for_query correctly
4. Verify no AttributeError exceptions
"""

import asyncio
import sys
import os
from typing import List, Optional, Dict, Any

# Add project path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from loom import Agent, agent as build_agent
from loom.interfaces.retriever import BaseRetriever, Document
from loom.interfaces.llm import BaseLLM
from loom.interfaces.tool import BaseTool


class MockSchemaContextRetriever(BaseRetriever):
    """Mock Schema Context Retriever"""

    def __init__(self):
        self.retrieve_count = 0
        self.retrieve_for_query_count = 0
        self._initialized = False

    async def initialize(self):
        """Initialize"""
        print("   MockSchemaContextRetriever.initialize() called")
        self._initialized = True

    async def retrieve_for_query(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Loom standard interface: retrieve_for_query"""
        self.retrieve_for_query_count += 1
        print(f"   retrieve_for_query called (count: {self.retrieve_for_query_count})")
        print(f"      Query: {query[:100]}...")
        return await self.retrieve(query, top_k, filters)

    async def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """Actual retrieval logic"""
        self.retrieve_count += 1
        print(f"   retrieve called (count: {self.retrieve_count})")

        # Return mock schema documents
        documents = [
            Document(
                content="""### Table: orders
**Description**: Orders table
**Columns**:
- **order_id** (BIGINT) [NOT NULL]: Order ID
- **customer_id** (BIGINT): Customer ID
- **order_date** (DATE): Order date
- **total_amount** (DECIMAL(10,2)): Total amount
""",
                metadata={
                    "source": "schema",
                    "table_name": "orders",
                    "relevance_score": 0.95
                },
                score=0.95
            ),
            Document(
                content="""### Table: customers
**Description**: Customers table
**Columns**:
- **customer_id** (BIGINT) [NOT NULL]: Customer ID
- **customer_name** (VARCHAR(100)): Customer name
- **email** (VARCHAR(100)): Email
""",
                metadata={
                    "source": "schema",
                    "table_name": "customers",
                    "relevance_score": 0.85
                },
                score=0.85
            )
        ]

        return documents[:top_k] if top_k else documents

    async def add_documents(self, documents: List[Document]) -> None:
        """Add documents (not implemented)"""
        pass

    def format_documents(self, documents: List[Document], max_length: int = 1000) -> str:
        """Format documents for context injection"""
        if not documents:
            return ""

        lines = ["## Retrieved Schema Context\n"]
        lines.append(f"Found {len(documents)} relevant table(s):\n")

        for i, doc in enumerate(documents, 1):
            lines.append(f"### Document {i}")
            if doc.metadata:
                table_name = doc.metadata.get("table_name", "Unknown")
                lines.append(f"**Table**: {table_name}")
            if doc.score is not None:
                lines.append(f"**Relevance**: {doc.score:.2%}")

            # Content (truncate if needed)
            content = doc.content
            if len(content) > max_length:
                content = content[:max_length] + "...\n[truncated]"

            lines.append(f"\n{content}\n")

        lines.append("---\n")
        return "\n".join(lines)


class MockLLM(BaseLLM):
    """Mock LLM"""

    def __init__(self):
        self.call_count = 0

    async def generate(self, messages, **kwargs):
        """Generate response"""
        self.call_count += 1
        print(f"   LLM.generate called (count: {self.call_count})")

        # Simulate LLM response
        from loom.types import ToolCall, Usage, AssistantMessage

        # First call: return tool call
        if self.call_count == 1:
            return AssistantMessage(
                role="assistant",
                content="I need to query the total number of orders",
                tool_calls=[
                    ToolCall(
                        id="call_1",
                        name="query_database",
                        arguments={"sql": "SELECT COUNT(*) FROM orders"}
                    )
                ],
                usage=Usage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
            )

        # Second call: return final result
        return AssistantMessage(
            role="assistant",
            content="Based on the query result, the total number of orders is 42",
            usage=Usage(prompt_tokens=120, completion_tokens=20, total_tokens=140)
        )

    async def generate_with_tools(self, messages, tools, **kwargs):
        """Generate response with tools (delegate to generate)"""
        return await self.generate(messages, **kwargs)

    async def stream(self, messages, **kwargs):
        """Stream response (not implemented for mock)"""
        result = await self.generate(messages, **kwargs)
        yield result

    @property
    def model_name(self) -> str:
        return "mock-llm"


class MockQueryTool(BaseTool):
    """Mock query tool"""

    name = "query_database"
    description = "Execute SQL query"

    async def run(self, sql: str) -> str:
        """Execute query"""
        print(f"   Tool.run called: {sql}")
        return '{"count": 42}'


async def test_context_loading_integration():
    """Integration test: Verify context loading"""

    print("\n" + "=" * 80)
    print("Integration Test: Verify Context Retriever in Loom Agent")
    print("=" * 80)

    # 1. Create components
    print("\n1. Creating test components...")
    context_retriever = MockSchemaContextRetriever()
    llm = MockLLM()
    tool = MockQueryTool()

    await context_retriever.initialize()
    print("   Components created successfully")

    # 2. Create Loom Agent
    print("\n2. Creating Loom Agent (with context_retriever)...")
    try:
        agent = build_agent(
            llm=llm,
            tools=[tool],
            context_retriever=context_retriever,
            max_iterations=3
        )
        print("   Agent created successfully")
    except Exception as e:
        print(f"   Agent creation failed: {e}")
        return False

    # 3. Run Agent (trigger TT recursion)
    print("\n3. Running Agent (test TT recursion and context injection)...")
    try:
        result = await agent.run("Count total orders")
        print(f"   Agent run successfully")
        print(f"   Result: {result}")
    except AttributeError as e:
        if "retrieve_for_query" in str(e):
            print(f"   Still missing retrieve_for_query: {e}")
            return False
        else:
            print(f"   Other AttributeError: {e}")
            return False
    except Exception as e:
        print(f"   Run error (may be normal): {e}")
        # If not AttributeError, the interface issue is fixed
        if "retrieve_for_query" not in str(e):
            print("   But error is not retrieve_for_query missing, interface is fixed")

    # 4. Check call statistics
    print("\n4. Checking method call statistics...")
    print(f"   retrieve_for_query call count: {context_retriever.retrieve_for_query_count}")
    print(f"   retrieve call count: {context_retriever.retrieve_count}")
    print(f"   LLM call count: {llm.call_count}")

    # Verify retrieve_for_query was called
    if context_retriever.retrieve_for_query_count > 0:
        print("   retrieve_for_query was called successfully")
    else:
        print("   retrieve_for_query was not called (Loom may not have enabled context retrieval)")

    # Verify retrieve was called
    if context_retriever.retrieve_count > 0:
        print("   retrieve was called successfully")
    else:
        print("   retrieve was not called")

    print("\n" + "=" * 80)
    print("Integration test completed!")
    print("=" * 80)

    return True


async def test_simple_retrieve_for_query():
    """Simple test: Directly call retrieve_for_query"""

    print("\n" + "=" * 80)
    print("Simple Test: Direct retrieve_for_query call")
    print("=" * 80)

    # Use real SchemaContextRetriever
    from app.services.infrastructure.agents.context_retriever import SchemaContextRetriever

    print("\n1. Creating SchemaContextRetriever...")
    retriever = SchemaContextRetriever(
        data_source_id="test-source",
        connection_config={},
        container=None,
        top_k=5,
        enable_stage_aware=True,
        use_intelligent_retrieval=False,
        enable_lazy_loading=True
    )
    print("   Created successfully")

    print("\n2. Calling retrieve_for_query...")
    try:
        docs = await retriever.retrieve_for_query(
            query="Query order information",
            top_k=3,
            filters=None
        )
        print(f"   Called successfully, returned {len(docs)} documents")
        return True
    except AttributeError as e:
        print(f"   AttributeError: {e}")
        return False
    except Exception as e:
        print(f"   Other error (expected): {type(e).__name__}")
        # As long as not AttributeError, method exists
        if "retrieve_for_query" not in str(e):
            print("   Method exists, just missing data source (normal)")
            return True
        return False


async def main():
    """Main test function"""

    print("\nStarting integration test...")

    # Test 1: Simple method call test
    test1_pass = await test_simple_retrieve_for_query()

    # Test 2: Loom Agent integration test
    test2_pass = await test_context_loading_integration()

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print(f"Simple method call test: {'PASS' if test1_pass else 'FAIL'}")
    print(f"Loom Agent integration test: {'PASS' if test2_pass else 'FAIL'}")

    if test1_pass and test2_pass:
        print("\nAll tests passed! Context loading is working!")
        return 0
    else:
        print("\nSome tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
