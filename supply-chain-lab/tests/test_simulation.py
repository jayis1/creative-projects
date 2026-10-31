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

    def test_receipt_fulfills_existing_backlog_first(self):
        node = Node('store', 1, 2, 8, 0, pipeline=[(1, 5)], backlog=4)
        node.receive(1)
        self.assertEqual(node.stock, 1)
        self.assertEqual(node.backlog, 0)

    def test_report_distinguishes_daily_shortfall_from_backlog(self):
        chain = Chain([Node('store', 1, 0, 1, 0)])
        result = chain.run([3, 0])
        self.assertEqual([day['unfilled_demand'] for day in result['daily']], [3, 0])
        self.assertEqual([day['backlog'] for day in result['daily']], [3, 0])
        self.assertEqual(result['customer_fill_rate'], 0.0)
        self.assertEqual(result['service_level'], 0.5)

    def test_zero_demand_has_perfect_fill_rate(self):
        result = Chain([Node('store', 1, 0, 1, 0)]).run([0, 0])
        self.assertEqual(result['customer_fill_rate'], 1.0)
        self.assertEqual(result['service_level'], 1.0)
        self.assertEqual(result['total_demand'], 0)

    def test_csv_report_is_exportable(self):
        import subprocess
        script = Path(__file__).resolve().parents[1] / 'main.py'
        scenario = Path(__file__).resolve().parents[1] / 'examples/basic.json'
        run = subprocess.run([sys.executable, str(script), str(scenario), '--format', 'csv'], capture_output=True, text=True, check=True, timeout=5)
        self.assertIn('name,ending_stock,backlog', run.stdout)
        self.assertIn('warehouse,', run.stdout)

if __name__ == '__main__':
    unittest.main()
