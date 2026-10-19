import math
import unittest
from prepare import temperature,configuration

class CaseTests(unittest.TestCase):
    def test_kernel_preserves_fresh_ends_and_symmetry(self):
        L=.004;w=.0002
        self.assertEqual(temperature(0,L,w,1800),298.)
        self.assertEqual(temperature(L,L,w,1800),298.)
        self.assertEqual(temperature(L/2,L,w,1800),1800.)
        for x in [.0001,.00195,.00203,.0039]:
            self.assertAlmostEqual(temperature(x,L,w,1800),temperature(L-x,L,w,1800),places=8)
    def test_timestep_pair_changes_only_cap_and_identity(self):
        a=configuration("phi110-dt100","full");b=configuration("phi110-dt050","full")
        differences={k for k in a if a[k]!=b[k]}
        self.assertEqual(differences,{"key","max_delta_t_s"})
        self.assertAlmostEqual(a["length_m"]/a["cells"],.5e-6)

if __name__=="__main__":unittest.main()
