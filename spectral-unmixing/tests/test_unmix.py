import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unmix import solve
class SolverTests(unittest.TestCase):
 def test_recovers_nonnegative_mixture(self):
  a=[[1,.1,0],[0,.9,.2],[.2,0,1],[.5,.3,.4]]; truth=[.2,.3,.5]
  y=[sum(row[i]*truth[i] for i in range(3)) for row in a]
  got=solve(a,y)
  for x,z in zip(got,truth): self.assertAlmostEqual(x,z,places=5)
 def test_rejects_shape(self):
  with self.assertRaises(ValueError): solve([[1,2],[3,4]],[1])
 def test_rejects_zero_signatures_and_nonfinite_values(self):
  with self.assertRaises(ValueError): solve([[0.0],[0.0]],[0.0,0.0])
  with self.assertRaises(ValueError): solve([[float('nan')]],[1.0])
 def test_rejects_nonpositive_steps(self):
  with self.assertRaises(ValueError): solve([[1.0]],[1.0],steps=0)
if __name__=='__main__': unittest.main()
