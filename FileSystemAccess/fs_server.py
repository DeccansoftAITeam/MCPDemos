"""Filesystem Resource Server — read-only access to documents under a sandboxed root.

Security model:
  * Sandbox: only files under ROOT are ever exposed.
  * Path containment: every request is resolved and checked to stay inside ROOT.
  * Read-only: no write/delete/move operations are exposed.
"""
import json
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Sandbox root: only files under here are exposed. Override with DOCS_ROOT.
ROOT = Path(os.environ.get("DOCS_ROOT", "./documents")).resolve()

mcp = FastMCP("Filesystem Resource Server")


def _safe_path(relative: str) -> Path:    
    """It returns a Path object — absolute path to the requested file or directory, 
    but only if that path is safely inside ROOT."""
    absolutePath = (ROOT / relative).resolve()
    if not absolutePath.is_relative_to(ROOT):
        raise ValueError(f"Access denied: '{relative}' is outside the sandbox")
    return absolutePath

@mcp.tool()
def list_documents(subdir: str = "") -> str:    
    """List readable documents under the sandbox root, recursively and paginated."""
    base = _safe_path(subdir)
    if not base.is_dir():
        raise ValueError(f"Not a directory: '{subdir}'")
    files = sorted(p for p in base.rglob("*") if p.is_file())
    total = len(files)    
    items = [str(p.relative_to(ROOT)) for p in files]
    return json.dumps({"root": str(ROOT), "total": total, "documents": items})

@mcp.tool()
def read_file(filepath: str) -> str:
    """Read any document (incl. nested) by its path relative to the sandbox root."""
    target = _safe_path(filepath)
    if not target.is_file():
        raise ValueError(f"Not a file: '{filepath}'")
    return target.read_text(encoding="utf-8", errors="replace")

@mcp.resource("docs://{filename}")
def read_document(filename: str) -> str:
    """Read a top-level document as an addressable resource (read-only context)."""
    target = _safe_path(filename)
    if not target.is_file():
        raise ValueError(f"Not a file: '{filename}'")
    return target.read_text(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    print(f"Serving read-only documents from {ROOT}", file=sys.stderr)
    mcp.run()
