from boa.core.project_files import script_paths
from boa.core.project_tree_data import FILES_FOLDER_ID, normalize_tree_layout, paired_graph_id


def _item(name, kind, uid, children=None):
    return {
        "name": name,
        "kind": kind,
        "id": uid,
        "protected": False,
        "children": children or [],
    }


def test_legacy_graph_and_script_roots_are_merged_and_paired():
    old = {
        "name": "Projet",
        "kind": "root",
        "id": "root",
        "protected": True,
        "children": [
            _item("Graphes", "folder", "graphs_root", [
                _item("outil.boa", "graph", "g_outil"),
                _item("pkg", "folder", "g_pkg", [_item("module.boa", "graph", "g_module")]),
            ]),
            _item("Fichiers Python", "folder", "scripts_root", [
                _item("outil.py", "script", "s_outil"),
                _item("pkg", "folder", "s_pkg", [_item("module.py", "script", "s_module")]),
            ]),
        ],
    }
    tree = normalize_tree_layout(old)
    files = next(child for child in tree["children"] if child["id"] == FILES_FOLDER_ID)
    assert [child["name"] for child in files["children"]] == ["pkg", "outil.py", "outil.boa"]
    pkg = files["children"][0]
    assert [child["name"] for child in pkg["children"]] == ["module.py", "module.boa"]
    assert paired_graph_id(tree, "s_outil") == "g_outil"
    assert paired_graph_id(tree, "s_module") == "g_module"


def test_script_paths_follow_the_shared_files_tree():
    tree = normalize_tree_layout({
        "name": "Projet",
        "kind": "root",
        "id": "root",
        "children": [
            _item("Fichiers", "folder", FILES_FOLDER_ID, [
                _item("main.py", "script", "s_main"),
                _item("pkg", "folder", "folder_pkg", [
                    _item("outil.py", "script", "s_outil"),
                    _item("outil.boa", "graph", "g_outil"),
                ]),
            ]),
        ],
    })
    assert script_paths(tree)["s_main"].as_posix() == "main.py"
    assert script_paths(tree)["s_outil"].as_posix() == "pkg/outil.py"
