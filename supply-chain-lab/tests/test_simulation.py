import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import Chain, Node, load_scenario

class BaselineTests(unittest.TestCase):
    def test_example_runs_and_reports_nodes(self):
        chain, demand = load_scenario(str(Path(__file__).resolve().parents[1] / 'examples/basic.json'))
        result = chain.run(demand)
        self.assertEqual(result['days'], 6)
        self.assertEqual([n['name'] for n in result['nodes']], ['warehouse', 'store'])

    def test_node_rejects_invalid_policy(self):
        with self.assertRaises(ValueError):
            Node('bad', 0, 4, 3, 1)

if __name__ == '__main__':
    unittest.main()
