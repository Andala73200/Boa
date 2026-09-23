import tempfile
import unittest
from pathlib import Path

from boa.core.project_environment import project_dependencies


class DependencySearchTests(unittest.TestCase):
    def test_search_covers_scripts_definitions_and_nested_graphs_with_aliases(self):
        project = {
            "context": {"imports": [{"statement": "import package_context as pc"}]},
            "scripts": {"s": {"name": "source.py", "content": "import package_script as ps"}},
            "graphs": {"g": {"graph": {"blocks": [{
                "id": "try", "key": "try",
                "try_graph": {"blocks": [{
                    "id": "raw", "key": "empty", "raw_code": "from package_nested import tool as t",
                }], "connections": []},
            }], "connections": []}}},
            "functions": {"f": {
                "imports": [{"statement": "import package_function as pf"}],
                "graph": {"blocks": [], "connections": []},
            }},
            "classes": {"c": {
                "imports": [{"statement": "from package_class import Base as B"}],
                "graph": {"blocks": [], "connections": []},
            }},
        }
        with tempfile.TemporaryDirectory() as folder:
            dependencies = project_dependencies(project, Path(folder) / "Boa_project.boa")
        modules = {item.module for item in dependencies}
        self.assertEqual(modules, {
            "package_context", "package_script", "package_nested",
            "package_function", "package_class",
        })


if __name__ == "__main__":
    unittest.main()
