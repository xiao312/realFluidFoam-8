import unittest
from history import assess


class HistoryPolicyTests(unittest.TestCase):
    def test_instantaneous_source_is_not_used_for_reported_speed(self):
        rows = []
        for t in [1e-6, 2e-6, 3e-6, 4e-6, 5e-6, 6e-6]:
            for side, sign in [('left', -1), ('right', 1)]:
                for stage in ['integrated_species_solve', 'instantaneous_end_step']:
                    for level in [1e-5, 2e-5, 3e-5]:
                        rows.append(dict(time_s=str(t),side=side,stage=stage,OH_level=str(level),
                            status='valid',speed_m_s=str(.06 if stage=='integrated_species_solve' else 999),
                            x_m=str(.002+sign*.4*t),U_local=str(sign*.1),rho_local='20',rho_unburned='100'))
        result = assess(rows)
        for side in ['left', 'right']:
            self.assertAlmostEqual(result['primary'][side]['tracking']['local_density_weighted_cm_s'],6)
            self.assertNotIn('instantaneous_end_step',result['primary'][side])
        self.assertLess(result['max_tracking_source_gap_cm_s'],1e-8)
        for row in rows:
            if float(row['OH_level'])==1e-5:
                row['status']='no_crossing'
        result=assess(rows)
        self.assertIn('left',result['primary'])
        self.assertIn('unresolved_reason',result['marker_checks']['left|1e-05'])


if __name__ == '__main__':
    unittest.main()
