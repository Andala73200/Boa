import unittest

from boa.core.graph_clone import clone_graph_fragment


class GraphCloneTests(unittest.TestCase):
    def test_clone_remaps_links_decorators_tp_and_nested_graphs(self):
        fragment = {
            "blocks": [
                {"id": "a", "key": "tp", "tp_pair_id": "pair", "x": 0, "y": 0},
                {"id": "b", "key": "tp", "tp_pair_id": "pair", "x": 10, "y": 0},
                {"id": "d", "key": "decorator", "decorator_target": "a", "decorator_attached": True},
                {"id": "loop", "key": "for", "loop_instance_number": 8, "inner_graph": {
                    "blocks": [{"id": "nested", "key": "value"}],
                    "connections": [],
                }},
            ],
            "connections": [
                {"source": "a", "source_port": "out", "target": "b", "target_port": "in"},
            ],
        }
        cloned = clone_graph_fragment(fragment)
        ids = {block["id"] for block in cloned["blocks"]}
        self.assertFalse(ids & {"a", "b", "d", "loop"})
        self.assertEqual(len(cloned["connections"]), 1)
        self.assertIn(cloned["connections"][0]["source"], ids)
        self.assertIn(cloned["connections"][0]["target"], ids)
        tp = [block for block in cloned["blocks"] if block["key"] == "tp"]
        self.assertEqual(tp[0]["tp_pair_id"], tp[1]["tp_pair_id"])
        decorator = next(block for block in cloned["blocks"] if block["key"] == "decorator")
        self.assertIn(decorator["decorator_target"], ids)
        loop = next(block for block in cloned["blocks"] if block["key"] == "for")
        self.assertNotIn("loop_instance_number", loop)
        self.assertNotEqual(loop["inner_graph"]["blocks"][0]["id"], "nested")


if __name__ == "__main__":
    unittest.main()
