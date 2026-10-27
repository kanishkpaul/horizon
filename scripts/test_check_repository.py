"""Regression checks for public-document and local-only repository boundaries."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import check_repository as repository


class RepositoryPolicyTests(unittest.TestCase):
    def test_missing_html_link_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            document = root / "README.md"
            document.write_text('<a href="docs/missing.md">Contract</a>\n')
            with patch.object(repository, "ROOT", root), patch.object(repository, "REQUIRED_DOCS", ()):
                errors = repository.check_documents([document])
            self.assertEqual(len(errors), 1)
            self.assertIn("missing link target", errors[0])

    def test_html_image_and_external_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "cover.svg").write_text("<svg/>")
            document = root / "README.md"
            document.write_text('<img src="cover.svg"/><a href="https://example.org">More</a>')
            with patch.object(repository, "ROOT", root), patch.object(repository, "REQUIRED_DOCS", ()):
                self.assertEqual(repository.check_documents([document]), [])

    def test_links_cannot_escape_repository(self):
        document = repository.ROOT / "README.md"
        with patch.object(Path, "read_text", return_value='<a href="../private.md">Private</a>'):
            errors = repository.check_documents([document])
        self.assertTrue(any("leaves repository" in error for error in errors))

    def test_forced_local_plan_and_research_are_rejected(self):
        paths = [repository.ROOT / ".local/BUILD_PLAN.md",
                 repository.ROOT / "docs/STRATEGY_REVIEW_2026-10-28.md"]
        self.assertEqual(len(repository.check_private_paths(paths)), 2)

    def test_public_contract_is_allowed(self):
        self.assertEqual(repository.check_private_paths([repository.ROOT / "docs/HSIM.md"]), [])

    def test_proposed_message_rejects_attribution(self):
        with tempfile.TemporaryDirectory() as directory:
            message = Path(directory) / "COMMIT_EDITMSG"
            message.write_text("docs: clarify status\n\nCo-Authored-By: Codex <agent@example.org>\n")
            self.assertTrue(repository.check_message(message))
            message.write_text("docs: clarify status\n")
            self.assertEqual(repository.check_message(message), [])

    def test_private_plan_is_not_required_for_a_clone(self):
        self.assertFalse(any(name.startswith(".local/") for name in repository.REQUIRED_DOCS))


if __name__ == "__main__":
    unittest.main()
