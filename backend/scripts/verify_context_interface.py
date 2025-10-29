#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify that SchemaContextRetriever fully implements Loom's ContextRetriever interface
"""

import sys
import os
import inspect

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.infrastructure.agents.context_retriever import SchemaContextRetriever


def verify_interface():
    """Verify SchemaContextRetriever has all required methods"""
    
    print("=" * 80)
    print("Verifying SchemaContextRetriever Interface")
    print("=" * 80)
    
    required_methods = {
        'retrieve_for_query': 'Loom standard method for retrieving documents',
        'retrieve': 'BaseRetriever standard method',
        'format_documents': 'Loom standard method for formatting documents',
        'add_documents': 'BaseRetriever standard method',
        'initialize': 'Initialization method'
    }
    
    all_pass = True
    
    for method_name, description in required_methods.items():
        print(f"\nChecking {method_name}...")
        print(f"  Description: {description}")
        
        if hasattr(SchemaContextRetriever, method_name):
            method = getattr(SchemaContextRetriever, method_name)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            print(f"  Status: EXISTS")
            print(f"  Parameters: {params}")
            
            # Check if it's async
            if inspect.iscoroutinefunction(method):
                print(f"  Type: async method")
            else:
                print(f"  Type: sync method")
                
        else:
            print(f"  Status: MISSING")
            all_pass = False
    
    print("\n" + "=" * 80)
    if all_pass:
        print("PASS: All required methods are present!")
    else:
        print("FAIL: Some methods are missing")
    print("=" * 80)
    
    return all_pass


if __name__ == "__main__":
    success = verify_interface()
    sys.exit(0 if success else 1)
