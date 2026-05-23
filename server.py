"""Local Flask API server for the BIST chat UI.

Endpoints:
  GET /report               → latest reports/*.md
  GET /files                → list of agents/memory/*.md
  GET /file?path=<rel>      → contents of a memory file (path-traversal safe)
  GET /masterplan           → agents/memory/masterplan.md
  GET /decisions            → latest agents/intelligence/decisions_*.md
"""
from pathlib import Path

from flask import Flask, abort, jsonify, request
from flask_cors import CORS

ROOT = Path(__file__).parent.resolve()
REPORTS_DIR = ROOT / "reports"
MEMORY_DIR = ROOT / "agents" / "memory"
INTELLIGENCE_DIR = ROOT / "agents" / "intelligence"

app = Flask(__name__)
CORS(app)


def _safe_resolve(base: Path, user_path: str) -> Path:
    """Resolve user_path under base; reject anything escaping the base dir."""
    candidate = (base / user_path).resolve()
    if base not in candidate.parents and candidate != base:
        abort(403, description="path outside allowed directory")
    return candidate


@app.get("/report")
def report():
    if not REPORTS_DIR.exists():
        return jsonify({"error": "reports dir not found"}), 404
    md_files = sorted(REPORTS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not md_files:
        return jsonify({"error": "no markdown reports found"}), 404
    latest = md_files[0]
    return jsonify({
        "filename": latest.name,
        "modified": latest.stat().st_mtime,
        "content": latest.read_text(encoding="utf-8"),
    })


@app.get("/files")
def files():
    if not MEMORY_DIR.exists():
        return jsonify({"files": []})
    items = []
    for p in sorted(MEMORY_DIR.glob("*.md")):
        items.append({
            "name": p.name,
            "size": p.stat().st_size,
            "modified": p.stat().st_mtime,
        })
    return jsonify({"files": items})


@app.get("/file")
def file():
    rel = request.args.get("path", "").strip()
    if not rel:
        return jsonify({"error": "missing path parameter"}), 400
    target = _safe_resolve(MEMORY_DIR, rel)
    if not target.exists() or not target.is_file():
        return jsonify({"error": "file not found"}), 404
    return jsonify({
        "filename": target.name,
        "content": target.read_text(encoding="utf-8"),
    })


@app.get("/masterplan")
def masterplan():
    path = MEMORY_DIR / "masterplan.md"
    if not path.exists():
        return jsonify({"error": "masterplan.md not found"}), 404
    return jsonify({
        "filename": path.name,
        "content": path.read_text(encoding="utf-8"),
    })


@app.get("/decisions")
def decisions():
    if not INTELLIGENCE_DIR.exists():
        return jsonify({"error": "intelligence dir not found"}), 404
    md_files = sorted(INTELLIGENCE_DIR.glob("decisions_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not md_files:
        return jsonify({"error": "no decisions found"}), 404
    latest = md_files[0]
    return jsonify({
        "filename": latest.name,
        "modified": latest.stat().st_mtime,
        "content": latest.read_text(encoding="utf-8"),
    })


@app.get("/")
def index():
    return jsonify({
        "service": "bist-local-api",
        "endpoints": ["/report", "/files", "/file?path=<name>", "/masterplan", "/decisions"],
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
