#!/usr/bin/env python3
"""
Generate secure session key for SRS Engine.
Run: python generate_secure_key.py
"""

import secrets

def generate_session_key():
    """Generate a cryptographically secure session key."""
    return secrets.token_urlsafe(32)

if __name__ == "__main__":
    key = generate_session_key()
    print("Generated secure session key:")
    print(f"SESSION_SECRET_KEY = {key}")
    print("\nAdd this to your .env file")
    print("Make sure to keep this key secret and secure!")
