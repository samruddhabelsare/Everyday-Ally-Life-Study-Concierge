# adk_probe.py
# Put this file in your project root and run: python adk_probe.py

import importlib
import sys
import traceback

print("Python executable:", sys.executable)
print("Current working dir:", __import__("os").getcwd())
print("--- Attempting to import google.adk ---")

try:
    adk = importlib.import_module("google.adk")
    attrs = [a for a in dir(adk) if not a.startswith("_")]
    print("ADK imported successfully.")
    print("ADK attributes (sample):", attrs[:200])
    print("has tool:", hasattr(adk, "tool"))
    print("has agent:", hasattr(adk, "agent"))
    print("has run_agent:", hasattr(adk, "run_agent"))
except Exception:
    print("Failed to import google.adk. Traceback below:")
    traceback.print_exc()
