#!/usr/bin/env python
"""
Setup validation script for PharmaAssist AI backend.
Run: python test_setup.py
"""
import sys

def test_imports():
    """Test all critical imports."""
    print("=" * 60)
    print("STEP 1: Testing Imports")
    print("=" * 60)
    try:
        import backend
        import backend.api.routes
        import backend.core.graph
        import backend.core.config
        import backend.agents.rag_agent
        import backend.tools.db_tools
        print("✓ All imports successful")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_config():
    """Test configuration loading."""
    print("\n" + "=" * 60)
    print("STEP 2: Testing Configuration")
    print("=" * 60)
    try:
        from backend.core import config
        print(f"✓ Config loaded")
        print(f"  - GROQ_API_KEY: {'SET' if config.GROQ_API_KEY else 'NOT SET'}")
        print(f"  - DB_HOST: {config.DB_HOST}")
        print(f"  - DB_NAME: {config.DB_NAME}")
        print(f"  - PDF_PATH: {config.PDF_PATH}")
        
        if not config.GROQ_API_KEY or config.GROQ_API_KEY == "your_groq_api_key_here":
            print("⚠ WARNING: GROQ_API_KEY not configured properly")
            return False
        return True
    except Exception as e:
        print(f"✗ Config failed: {e}")
        return False

def test_graph():
    """Test graph compilation."""
    print("\n" + "=" * 60)
    print("STEP 3: Testing Graph Compilation")
    print("=" * 60)
    try:
        from backend.core.graph import build_graph
        graph = build_graph()
        nodes = list(graph.nodes.keys())
        print(f"✓ Graph compiled successfully")
        print(f"  - Nodes: {', '.join(nodes)}")
        return True
    except Exception as e:
        print(f"✗ Graph compilation failed: {e}")
        return False

def test_api():
    """Test API initialization."""
    print("\n" + "=" * 60)
    print("STEP 4: Testing API Initialization")
    print("=" * 60)
    try:
        from backend.api.routes import app
        routes = [r.path for r in app.routes if hasattr(r, 'path')]
        print(f"✓ FastAPI app created")
        print(f"  - Routes: {', '.join(routes)}")
        return True
    except Exception as e:
        print(f"✗ API initialization failed: {e}")
        return False

def test_rag():
    """Test RAG system."""
    print("\n" + "=" * 60)
    print("STEP 5: Testing RAG System")
    print("=" * 60)
    try:
        from backend.agents.rag_agent import get_rag_collection
        collection = get_rag_collection()
        count = collection.count()
        print(f"✓ RAG initialized")
        print(f"  - Collection: {collection.name}")
        print(f"  - Documents: {count}")
        return True
    except Exception as e:
        print(f"✗ RAG initialization failed: {e}")
        return False

def test_database():
    """Test database connectivity."""
    print("\n" + "=" * 60)
    print("STEP 6: Testing Database Connectivity")
    print("=" * 60)
    try:
        from backend.tools.db_tools import get_conn
        conn = get_conn()
        print(f"✓ Database connection successful")
        conn.close()
        return True
    except Exception as e:
        print(f"⚠ Database connection failed (this is OK if DB not running): {e}")
        return None  # None means optional failure

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PHARMAASSIST AI - SETUP VALIDATION")
    print("=" * 60)
    
    results = {
        "Imports": test_imports(),
        "Configuration": test_config(),
        "Graph": test_graph(),
        "API": test_api(),
        "RAG": test_rag(),
        "Database": test_database(),
    }
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, result in results.items():
        if result is True:
            print(f"✓ {name}: PASS")
        elif result is False:
            print(f"✗ {name}: FAIL")
        else:
            print(f"⚠ {name}: OPTIONAL (not critical)")
    
    critical_passed = all(v for k, v in results.items() if k != "Database" and v is not None)
    
    print("\n" + "=" * 60)
    if critical_passed:
        print("🟢 FINAL VERDICT: READY TO RUN")
        print("=" * 60)
        print("\nTo start the server:")
        print("  uvicorn backend.api.routes:app --reload --port 8000")
        print("\nTo start Streamlit (optional):")
        print("  streamlit run backend/streamlit_app.py")
        return 0
    else:
        print("🔴 FINAL VERDICT: NEEDS FIXES")
        print("=" * 60)
        print("\nPlease fix the failed tests above before running.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
