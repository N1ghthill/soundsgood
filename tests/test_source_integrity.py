import ast
from pathlib import Path
import unittest


class SourceIntegrityTest(unittest.TestCase):
    def test_modules_using_gettext_alias_import_it(self):
        source_root = Path(__file__).parents[1] / "soundsgood"
        missing = []
        for path in source_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            uses_gettext_alias = any(
                isinstance(node, ast.Name)
                and node.id == "_"
                and isinstance(node.ctx, ast.Load)
                for node in ast.walk(tree)
            )
            if not uses_gettext_alias:
                continue
            imports_gettext_alias = any(
                isinstance(node, ast.ImportFrom)
                and node.module == "gettext"
                and any(
                    alias.name in {"gettext", "_"}
                    and (alias.asname or alias.name) == "_"
                    for alias in node.names
                )
                for node in tree.body
            )
            if not imports_gettext_alias:
                missing.append(str(path.relative_to(source_root.parent)))
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
