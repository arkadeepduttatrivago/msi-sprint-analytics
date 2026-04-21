"""Helper: read MCP response file, save issues, print stats."""
import json, sys

src = sys.argv[1]
dst = sys.argv[2]

with open(src, "r", encoding="utf-8") as f:
    data = json.load(f)

issues = data["issues"]
print(f"Issues: {len(issues)}")
print(f"isLast: {data.get('isLast')}")

with open(dst, "w", encoding="utf-8") as f:
    json.dump(issues, f, ensure_ascii=False)

print(f"Saved to {dst}")

if data.get("nextPageToken"):
    print(f"NEXT_TOKEN: {data['nextPageToken']}")
