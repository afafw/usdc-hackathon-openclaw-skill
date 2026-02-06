#!/usr/bin/env python3
"""Weather lookup using wttr.in — no API key needed."""
import sys
import urllib.request

def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=3"
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode().strip()

if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "London"
    print(get_weather(city))
