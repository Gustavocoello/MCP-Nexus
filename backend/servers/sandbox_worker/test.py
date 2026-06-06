# test_sandbox.py (ponlo en sandbox_worker/)
import sys
sys.path.insert(0, r"C:\work\mcp-nexus\mcp-scratch\backend")

from src.services.agent.Koda.tools.sandbox_client import execute_in_sandbox

print("=== Test 1: Python ===")
print(execute_in_sandbox("python3 --version"))

print("\n=== Test 2: Node ===")
print(execute_in_sandbox("node --version"))

print("\n=== Test 3: Script real ===")
print(execute_in_sandbox("python3 -c \"print(2+2)\""))