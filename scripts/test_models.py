#!/usr/bin/env python3
"""Test which Claude models are available."""
import os

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Try different model names
models_to_try = [
    "claude-3-5-sonnet-latest",
    "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20240620",
    "claude-3-opus-latest",
    "claude-3-opus-20240229",
    "claude-3-sonnet-20240229",
    "claude-3-haiku-20240307",
]

print("Testing Claude model availability...\n")

for model in models_to_try:
    try:
        response = client.messages.create(
            model=model, max_tokens=10, messages=[{"role": "user", "content": "Hi"}]
        )
        print(f"✓ {model} - WORKS")
    except Exception as e:
        error_msg = str(e)
        if "not_found_error" in error_msg:
            print(f"✗ {model} - NOT FOUND")
        else:
            print(f"✗ {model} - ERROR: {error_msg[:50]}")
