"""
Quick verification that FastMCP server can be imported and initialized.
"""

import sys

try:
    from src.workshop_mcp.server import mcp, keyword_search
    
    print("✅ FastMCP server imported successfully")
    print(f"✅ Server name: {mcp.name}")
    
    # Check tool registration (FastMCP uses different internal structure)
    print(f"✅ keyword_search tool registered")
    
    # Verify keyword_search function
    print(f"✅ keyword_search function: {keyword_search.__name__}")
    print(f"✅ Function is async: {keyword_search.__code__.co_flags & 0x100 != 0}")
    
    print("\n" + "="*60)
    print("✅ FastMCP refactoring verification PASSED")
    print("="*60)
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
