import unittest
import numpy as np
from analyze import contour


class UnitAndSignTests(unittest.TestCase):
    def test_mass_source_density_weight_and_two_front_sign(self):
        x=np.linspace(0,.004,41)
        data={'x_m':x,'YOH':.02*np.minimum(x,.004-x),
              'gradOH_1_m':np.where(x<.002,.02,-.02),
              'rho_kg_m3':np.full(41,20.),'rho_unburned_kg_m3':np.full(41,100.),
              'omegaOH_kg_m3_s':np.full(41,.12),
              'diffusion_used_kg_m3_s':np.zeros(41),
              'diffusion_Fick_kg_m3_s':np.full(41,.04)}
        for side in ['left','right']:
            result=contour(data,2e-5,side)
            self.assertAlmostEqual(result['speed_cm_s'],6.)
            self.assertAlmostEqual(result['fick_speed_cm_s'],8.)
        data['omegaOH_kg_m3_s']*=-1
        self.assertAlmostEqual(contour(data,2e-5)['speed_cm_s'],-6.)
