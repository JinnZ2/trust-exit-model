"""Structural invariants — pins the claims that drifted in the 2026-08-15 audit.

These do not test the model. They test the repo's claims *about* the model,
which is the layer that had rotted (F1-F4 in docs/method.md): a stale test
count, a structure block missing a third of its modules, and a package that
did not export its own published contract surface.

Prose does not stay true on its own. These make the drift fail the suite.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC = REPO_ROOT / "src"
TESTS = REPO_ROOT / "tests"
LEGACY = REPO_ROOT / "legacy"
EXAMPLES = REPO_ROOT / "examples"
TOOLS = REPO_ROOT / "tools"
README = REPO_ROOT / "README.md"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


def _count_test_functions() -> int:
    """Count `def test_*` across tests/, module-level and inside classes.

    No test in this suite is parametrized, so this equals pytest's collected
    count. If parametrization is ever introduced, this helper must change with
    it — that is intentional, so the count claim cannot silently decouple.
    """
    total = 0
    for path in sorted(TESTS.glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    total += 1
    return total


def _src_module_names() -> set[str]:
    return {p.stem for p in SRC.glob("*.py") if p.stem != "__init__"}


class TestDocumentedTestCount:
    """F1: README claimed 54 tests when the suite had 79."""

    def test_readme_count_matches_suite(self) -> None:
        actual = _count_test_functions()
        match = re.search(r"Test suite \((\d+) tests\)", README.read_text(encoding="utf-8"))
        assert match is not None, "README structure block lost its test-count claim"
        claimed = int(match.group(1))
        assert claimed == actual, (
            f"README claims {claimed} tests, suite has {actual}. "
            "Update the README structure block."
        )

    def test_claude_md_count_matches_suite(self) -> None:
        actual = _count_test_functions()
        match = re.search(r"pytest test suite \((\d+) tests\)", CLAUDE_MD.read_text(encoding="utf-8"))
        assert match is not None, "CLAUDE.md lost its test-count claim"
        claimed = int(match.group(1))
        assert claimed == actual, (
            f"CLAUDE.md claims {claimed} tests, suite has {actual}."
        )


class TestDocumentedStructure:
    """F2/F3: structure blocks silently fell behind the tree."""

    def test_readme_lists_every_src_module(self) -> None:
        readme = README.read_text(encoding="utf-8")
        missing = sorted(m for m in _src_module_names() if f"{m}.py" not in readme)
        assert not missing, (
            f"src modules absent from README structure block: {missing}"
        )

    def test_claude_md_lists_every_src_module(self) -> None:
        claude_md = CLAUDE_MD.read_text(encoding="utf-8")
        missing = sorted(m for m in _src_module_names() if f"{m}.py" not in claude_md)
        assert not missing, (
            f"src modules absent from the CLAUDE.md architecture tables: {missing}"
        )


class TestPackageExports:
    """F4: __all__ omitted the contract surface CLAUDE.md publishes."""

    def test_all_names_resolve(self) -> None:
        import src

        unresolved = sorted(n for n in src.__all__ if not hasattr(src, n))
        assert not unresolved, f"src.__all__ names nothing importable: {unresolved}"

    def test_contract_surface_is_exported(self) -> None:
        import src

        # Named in CLAUDE.md's "Published Contract" section; external consumers
        # decode against these, so they must be reachable from the package root.
        required = {
            "TrustPhase",
            "TrustState",
            "CustomerSegment",
            "Customer",
            "CONTRACT_VERSION",
            "export_payload",
            "export_trust_state",
        }
        missing = sorted(required - set(src.__all__))
        assert not missing, f"published contract names not exported: {missing}"


class TestLegacyIsolation:
    """legacy/ is retained for precedence, but must stay off the load path."""

    def test_legacy_folder_is_documented(self) -> None:
        assert (LEGACY / "README.md").exists(), (
            "legacy/ must carry a README stating, per module, whether it was "
            "superseded or unwired"
        )

    def test_nothing_live_imports_legacy(self) -> None:
        offenders: list[str] = []
        for directory in (SRC, TESTS, EXAMPLES, TOOLS):
            for path in sorted(directory.glob("*.py")):
                if path.name == Path(__file__).name:
                    continue  # this file names `legacy` only as a string
                tree = ast.parse(path.read_text(encoding="utf-8"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        if (node.module or "").split(".")[0] == "legacy":
                            offenders.append(f"{path.name}:{node.lineno}")
                    elif isinstance(node, ast.Import):
                        for alias in node.names:
                            if alias.name.split(".")[0] == "legacy":
                                offenders.append(f"{path.name}:{node.lineno}")
        assert not offenders, (
            f"live code imports from legacy/: {offenders}. Retained modules are a "
            "record, not a dependency — re-wire it into src/ instead."
        )

    def test_legacy_modules_remain_importable(self) -> None:
        # Retention means readable *and* runnable. A legacy module that no longer
        # imports has decayed into a text file.
        import importlib

        for path in sorted(LEGACY.glob("*.py")):
            if path.stem == "__init__":
                continue
            importlib.import_module(f"legacy.{path.stem}")


class TestMethodRecord:
    """The loop only survives if the record is actually there."""

    def test_method_doc_exists_with_required_sections(self) -> None:
        method = REPO_ROOT / "docs" / "method.md"
        assert method.exists(), "docs/method.md is the falsification record"
        text = method.read_text(encoding="utf-8")
        for section in ("## Claim register", "## Falsification log", "## Open unknowns"):
            assert section in text, f"docs/method.md lost its {section!r} section"

    def test_open_unknowns_are_numbered(self) -> None:
        text = (REPO_ROOT / "docs" / "method.md").read_text(encoding="utf-8")
        unknowns = set(re.findall(r"\*\*(U\d+)\*\*", text))
        assert len(unknowns) >= 5, (
            f"expected the open-unknowns register to be populated, found {unknowns}"
        )
