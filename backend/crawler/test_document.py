"""
Run this standalone to see what your crawler's requests.Session
actually receives from scholarships.gov.in.

Usage: python diagnose_fetch.py
"""

import requests

url = "https://scholarships.gov.in/All-Scholarships"

session = requests.Session()
session.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    )
})

response = session.get(url, timeout=(10, 30), allow_redirects=True)

print(f"Status code   : {response.status_code}")
print(f"Final URL     : {response.url}")
print(f"Content length: {len(response.text)}")
print(f"Set-Cookie    : {response.headers.get('Set-Cookie')}")
print()

marker = "Scheme Open from"
found = marker in response.text
print(f"Contains '{marker}'? -> {found}")

if not found:
    # Save it so you can actually look at what you got
    with open("actual_response.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("\nSaved raw response to actual_response.html — open it and check for:")
    print(" - A CAPTCHA / 'please enable JavaScript' / 'checking your browser' message")
    print(" - Whether the scheme list section is present at all in raw HTML")
    print(f"\nFirst 1000 chars of response:\n{response.text[:1000]}")