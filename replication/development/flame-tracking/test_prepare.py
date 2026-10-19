import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from prepare import prepare


class RestartTests(unittest.TestCase):
    def test_observer_changes_only_copied_controls_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parents[4]) as directory:
            root=Path(directory);donor=root/'jobs/124878193/case'
            (donor/'constant').mkdir(parents=True);(donor/'system').mkdir()
            (donor/'paper-case.json').write_text('{"phi":1.1}')
            (donor/'constant/thermophysicalProperties').write_text('idKineticMixture perfectGas janaf sutherlandKinetic')
            (donor/'constant/flameSpeedProperties').write_text('enabled true; interval 10;')
            original='startFrom startTime; startTime 0; endTime .0002; deltaT 5e-8; adjustTimeStep yes; writeControl runTime; writeInterval 1e-5; runTimeModifiable yes;'
            (donor/'system/controlDict').write_text(original)
            for rank in range(8):
                (donor/f'processor{rank}/constant').mkdir(parents=True)
                folder=donor/f'processor{rank}/2.00180632513e-05';folder.mkdir()
                for name in ['T','p','U','rho','OH','CH4','Qdot']:(folder/name).write_text('fixture '+name)
            job=root/'jobs/999'
            with contextlib.redirect_stdout(io.StringIO()):
                prepare('plan',job,'phi110','qualify',root)
                self.assertFalse(job.exists())
                prepare('apply',job,'phi110','qualify',root)
            self.assertEqual((donor/'system/controlDict').read_text(),original)
            self.assertIn('enabled false',(job/'off/constant/frontTrackingProperties').read_text())
            config=json.loads((job/'tracking-plan.json').read_text())
            self.assertAlmostEqual(config['temperature_anchor']['temperature_anchor_K'],780.8722452267356)
            self.assertEqual((job/'on/processor0/2.00180632513e-05/T').read_text(),'fixture T')
            with self.assertRaises(ValueError):prepare('apply',job,'phi110','qualify',root)


if __name__=='__main__':unittest.main()
