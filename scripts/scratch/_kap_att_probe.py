"""Quick attachment URL probe for KAP disclosure 1574461."""
import re
import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
url = "https://www.kap.org.tr/tr/Bildirim/1574461"
r = requests.get(url, headers=headers, timeout=30)
print("Status:", r.status_code)

# All href patterns
all_hrefs = re.findall(r'href=["\'`]([^"\'`]+)["\'`]', r.text, re.I)
print(f"\nTotal hrefs: {len(all_hrefs)}")
keywords = ["file", "download", "pdf", "export", "eki", "attachment", "excel", "word", "doc"]
for h in all_hrefs:
    if any(k in h.lower() for k in keywords):
        print(" ", h)

# Also look for onclick or data-url patterns
data_hrefs = re.findall(r'data-href=["\'`]([^"\'`]+)["\'`]', r.text, re.I)
print(f"\nData-hrefs: {len(data_hrefs)}")
for h in data_hrefs[:10]:
    print(" ", h)

# Look for any URL-like path segments that look like attachments
paths = re.findall(r'/[a-zA-Z0-9/_-]+\.(?:pdf|xlsx|xls|docx|doc)\b', r.text, re.I)
print(f"\nFile path patterns: {len(paths)}")
for p in paths[:20]:
    print(" ", p)

# Save a snippet of the HTML around "ek" or "dosya" for context
for m in re.finditer(r'.{0,100}(?:ekdosya|ek-dosya|bildirim.eki|attachment).{0,100}', r.text, re.I):
    print("\nContext:", m.group())

# Count timestamps
ts = re.findall(r'\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}:\d{2}', r.text)
print("\nTimestamps:", ts[:5])
