"""
Initialize Policy Vector Database

Run this script to create the vector database from policy documents.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools.utils.vector_db_manager import initialize_policy_vector_db


def main():
    """Initialize the policy vector database."""
    print("=" * 80)
    print("POLICY VECTOR DATABASE INITIALIZATION")
    print("=" * 80 + "\n")
    
    # Check if documents directory exists
    docs_dir = "data/documents"
    if not os.path.exists(docs_dir):
        os.makedirs(docs_dir)
        print(f"📁 Created {docs_dir} directory")
        print(f"❌ Please add policy documents (.txt, .pdf, .md) to this directory and run again")
        return
    
    # Initialize
    try:
        manager = initialize_policy_vector_db(docs_dir)
        
        if manager.vector_store:
            print("\n" + "=" * 80)
            print("✅ SUCCESS: Policy vector database is ready!")
            print("=" * 80)
            print(f"   Database location: {manager.db_path}")
            
            # Test search
            print("\n🧪 Testing search functionality...")
            test_query = "What is the return policy?"
            print(f"   Query: '{test_query}'")
            results = manager.similarity_search(test_query, k=3)
            
            if results:
                print(f"   ✅ Search test passed - found {len(results)} results")
                print(f"\n   Top result (score: {results[0]['score']}):")
                print(f"   {results[0]['content'][:200]}...")
            else:
                print("   ⚠️  Search test returned no results")
        else:
            print("\n" + "=" * 80)
            print("⚠️  WARNING: Vector database not created")
            print("=" * 80)
            print("   Possible reasons:")
            print("   - No documents found in data/documents/")
            print("   - Documents couldn't be loaded")
            print("   - Chunking failed")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()