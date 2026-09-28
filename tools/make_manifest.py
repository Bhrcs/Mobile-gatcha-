"""Writes Content/data/manifest.json: the JSON files in each data folder.
The game reads this instead of listing folders (folder listing is not portable
inside Android APKs). Run after adding or removing data files."""
import json, os
root = os.path.join(os.path.dirname(__file__), "..", "Content", "data")
out = {d: sorted(f for f in os.listdir(os.path.join(root, d)) if f.endswith(".json"))
       for d in sorted(os.listdir(root)) if os.path.isdir(os.path.join(root, d))}
json.dump(out, open(os.path.join(root, "manifest.json"), "w"), indent=1)
print({k: len(v) for k, v in out.items()})
