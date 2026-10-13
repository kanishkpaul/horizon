"""Check repository contracts, local document links, and new commit attribution."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys
import tomllib
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DOCS = (
    "README.md", "AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "SECURITY.md",
    "docs/PROJECT.md", "docs/ARCHITECTURE.md", "docs/BUILD_PLAN.md",
    "docs/DECISIONS.md", "docs/CODE_STYLE.md", "docs/FEATURES.md",
    "docs/HSIM.md", "docs/HDB.md", "docs/MODELS.md", "docs/VALIDATION.md",
    "docs/MIGRATION.md", "hsim/README.md", "hsim/AGENTS.md",
    "hdb/README.md", "hdb/AGENTS.md",
)
AGENT_NAMES = r"(?:claude|codex|copilot|chatgpt|anthropic|openai|gemini|cursor|coding[- ]agent)"
ATTRIBUTION = re.compile(
    rf"(?im)^(?:co-authored-by|signed-off-by):[^\n]*\b{AGENT_NAMES}\b"
    rf"|\b(?:generated|written|built|implemented|authored|assisted|powered)"
    rf"\s+(?:by|with)\s+{AGENT_NAMES}\b"
)


def git(*args: str) -> str:
    """Run read-only Git queries and surface failures to the caller."""
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def repository_paths() -> list[Path]:
    names = git("ls-files", "--cached", "--others", "--exclude-standard", "-z")
    return sorted({ROOT / name for name in names.split("\0") if name and (ROOT / name).is_file()})


def check_documents(paths: list[Path]) -> list[str]:
    errors = [f"Missing required document: {name}" for name in REQUIRED_DOCS if not (ROOT / name).is_file()]
    for path in paths:
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"(?ms)^```.*?^```[^\n]*", "", text)
        for target in re.findall(r"\[[^\]]*\]\(([^\s)]+)\)", text):
            target = target.strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            linked = (path.parent / unquote(parsed.path)).resolve()
            if not linked.is_relative_to(ROOT):
                errors.append(f"{path.relative_to(ROOT)}: link leaves repository: {target}")
            elif not linked.exists():
                errors.append(f"{path.relative_to(ROOT)}: missing link target: {target}")
    return errors


def dependency_tables(value: dict):
    for key, child in value.items():
        if key in {"dependencies", "dev-dependencies", "build-dependencies"}:
            yield child
        elif isinstance(child, dict):
            yield from dependency_tables(child)


def check_boundaries() -> list[str]:
    errors = []
    workspace = tomllib.loads((ROOT / "Cargo.toml").read_text())
    members = workspace["workspace"]["members"]
    for owner, peer in (("hsim", "hdb"), ("hdb", "hsim")):
        if owner not in members:
            errors.append(f"Workspace is missing {owner}")
        manifest_path = ROOT / owner / "Cargo.toml"
        manifest = tomllib.loads(manifest_path.read_text())
        for table in dependency_tables(manifest):
            for name, spec in table.items():
                package = spec.get("package", name) if isinstance(spec, dict) else name
                path = spec.get("path") if isinstance(spec, dict) else None
                imports_peer = package == peer or (path and (manifest_path.parent / path).resolve() == ROOT / peer)
                if imports_peer:
                    errors.append(f"{owner} must not depend on {peer}")
                if owner == "hsim" and package in {"tauri", "rusqlite", "reqwest", "ort", "fastembed"}:
                    errors.append(f"hsim must not depend on {package}; keep I/O and providers outside the engine")
    return errors


def check_private_paths(paths: list[Path]) -> list[str]:
    errors = []
    private_roots = {"data", "workspaces", "backups", "models", "indexes", "runs"}
    for path in paths:
        relative = path.relative_to(ROOT)
        if relative.parts[0] in private_roots:
            errors.append(f"Private workspace path in repository: {relative}")
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            errors.append(f"Environment secrets file in repository: {relative}")
        if re.search(r"\.(?:sqlite3?|db)(?:-wal|-shm|-journal)?$", path.name):
            errors.append(f"Database file in repository: {relative}")
    return errors


def check_commits(commit_range: str | None) -> list[str]:
    baseline = (ROOT / ".commit-policy-base").read_text().strip()
    if not commit_range:
        subprocess.run(["git", "merge-base", "--is-ancestor", baseline, "HEAD"], cwd=ROOT, check=True)
        commit_range = f"{baseline}..HEAD"
    errors = []
    for commit in git("rev-list", commit_range).splitlines():
        message = git("show", "-s", "--format=%B", commit)
        if ATTRIBUTION.search(message):
            errors.append(f"Coding-agent attribution in commit {commit[:12]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit-range", help="Override the range after the preserved legacy baseline")
    args = parser.parse_args()
    try:
        paths = repository_paths()
        errors = check_documents(paths) + check_boundaries() + check_private_paths(paths) + check_commits(args.commit_range)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(f"Repository check could not complete: {error}", file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("Repository contracts, local document links, private paths, and new commit messages checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
