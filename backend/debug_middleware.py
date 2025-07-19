#!/usr/bin/env python3
"""
Debug middleware configuration to find the malformed entry
"""

import sys
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

print("Creating FastAPI app and debugging middleware...")

# Import everything that main.py imports
import os
from dotenv import load_dotenv
import json
import logging
from datetime import datetime
from providers import ProviderManager, ProviderError
from logger import event_logger
from search_tools import WebSearchManager, SearchError
from agent_mode import AgentMode
from file_tools import FileSystemTools
from gmail_service import email_service

load_dotenv()

app = FastAPI(title="Research Agent API", version="1.0.0")

print("FastAPI app created")
print(f"Initial middleware: {app.user_middleware}")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print(f"After adding CORS middleware: {app.user_middleware}")

# Initialize all the same objects as main.py to see if any of them add middleware
print("Initializing provider manager...")
provider_manager = ProviderManager()
print(f"After provider manager: {app.user_middleware}")

print("Initializing web search manager...")
web_search_manager = WebSearchManager()
print(f"After web search manager: {app.user_middleware}")

print("Initializing file system...")
file_system = FileSystemTools()
print(f"After file system: {app.user_middleware}")

print("Initializing agent mode...")
max_agent_steps = int(os.getenv("AGENT_MAX_STEPS", 10))
agent_mode = AgentMode(web_search_manager, file_system, max_steps=max_agent_steps)
print(f"After agent mode: {app.user_middleware}")

print("\nInspecting middleware entries:")
for i, middleware in enumerate(app.user_middleware):
    print(f"Middleware {i}: {middleware}")
    print(f"  Type: {type(middleware)}")
    print(f"  Length: {len(middleware) if hasattr(middleware, '__len__') else 'N/A'}")
    if hasattr(middleware, '__len__') and len(middleware) > 2:
        print(f"  PROBLEM: This middleware has {len(middleware)} values instead of 2!")
        for j, item in enumerate(middleware):
            print(f"    Item {j}: {item}")

print("\nTrying to build middleware stack...")
try:
    middleware_stack = app.build_middleware_stack()
    print("[OK] Middleware stack built successfully")
except Exception as e:
    print(f"[ERROR] Failed to build middleware stack: {e}")
    traceback.print_exc()