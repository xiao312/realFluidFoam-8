"""Run with python -B replication/suite/test_suite.py; no solver or network needed."""
import unittest
from pathlib import Path
import numpy as np
from common import HERE, REPLICATION, affine, contained, read_json
from datasets import series
from flame_speed import track, estimate


class SuiteTests(unittest.TestCase):
    def test_all_calibrations_map_both_inspected_ticks(self):
        styles=read_json(HERE/"styles.json")["figures"]
        inventory={r["id"]:r for r in read_json(REPLICATION/"validation/figures/inventory.json")}
        for key,style in styles.items():
            cl,ct,cr,cb=inventory[key]["crop"]
            for panel in style["panels"].values():
                l,t,r,b=panel["rect"]
                self.assertTrue(cl<=l<r<=cr and ct<=t<b<=cb)
                for cal in [panel["x"],*panel["y"].values()]:
                    np.testing.assert_allclose(affine(np.array([cal[1],cal[3]]),cal),[cal[0],cal[2]],rtol=0,atol=1e-10)

    def test_project_escape_and_root_are_rejected(self):
        for path in [Path("../escape"),Path(".")]:
            with self.assertRaises(ValueError): contained(HERE,path)

    def test_nonfinite_or_mismatched_series_is_rejected(self):
        for x,y in [([1],[float("nan")]),([1,2],[3]),([],[])]:
            with self.assertRaises(ValueError): series("f","p","T",x,y,"test")

    def test_actual_irregular_times_and_density_weighted_speed(self):
        t=np.array([0,1,2.7,4.1,5])*1e-5
        rows=np.column_stack([t,.001+.03*t,np.full(5,.12),np.full(5,8.),.001+.03*t,np.full(5,.09)])
        result=estimate(rows,12.,5e-5)
        self.assertAlmostEqual(result["OH_speed_cm_s"],6.,places=8)
        self.assertAlmostEqual(result["temperature_speed_cm_s"],6.,places=8)
        self.assertEqual(result["samples"],5)

    def test_short_history_is_not_a_flame_speed(self):
        rows=np.zeros((3,6));rows[:,0]=[0,1e-6,2e-6]
        with self.assertRaises(ValueError): estimate(rows,1.,5e-5)

    def test_missing_oh_is_not_zero_filled(self):
        job={"job":"test","metadata":{"config":{"cells":20,"length_m":.002}},
             "samples":[{"time_s":0,"fields":{"T":[300]*20,"rho":[1]*20,"U":[.1]*20}}]}
        with self.assertRaisesRegex(ValueError,"OH"): track(job)

    def test_catalog_targets_exist(self):
        for family in read_json(HERE/"catalog.json")["families"]:
            for key in ("entrypoint","guide"): self.assertTrue((REPLICATION/family[key]).is_file(),family[key])


if __name__=="__main__": unittest.main()
