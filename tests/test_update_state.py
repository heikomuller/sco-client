import os
import sys
import unittest
import urllib2

import scocli

API_URL = 'http://localhost:5000/sco-server/api/v1'
DATA_DIR = os.path.abspath('./data')

class TestSCOClient(unittest.TestCase):

    def setUp(self):
        """Initialize the SCO Client. Assumes that defautl Web API is active."""
        self.RESULT_FILE = os.path.join(DATA_DIR, 'result.tar.gz')
        self.sco = scocli.SCOClient(api_url=API_URL)

    def test_create_error_run(self):
        """Test SCO client update state method. Create new experiment run and
        update state to 'FAILED'."""
        # Create experiment for first pair of subject and image group
        subject = self.sco.subjects_get(self.sco.subjects_list()[0].url)
        image_group = self.sco.image_groups_get(self.sco.image_groups_list()[0].url)
        experiment = self.sco.experiments_create(
            'Update state experiment',
            subject.identifier,
            image_group.identifier,
            properties={'comment':'Experiment created automatically to test model run update state'}
        )
        run = experiment.run('Test Run', arguments={'max_eccentricity':11})
        self.assertTrue(run.state.is_idle)
        run = run.update_state_active()
        self.assertTrue(run.state.is_running)
        run = run.update_state_error(['Something went wrong'])
        self.assertTrue(run.state.is_failed)
        # Ensure that we cannot modify state anymore
        with self.assertRaises(ValueError):
            run = run.update_state_active()

    def test_create_success_run(self):
        """Test SCO client update state method. Create new experiment run and
        update state to 'SUCCESS'."""
        # Create experiment for first pair of subject and image group
        subject = self.sco.subjects_get(self.sco.subjects_list()[0].url)
        image_group = self.sco.image_groups_get(self.sco.image_groups_list()[0].url)
        experiment = self.sco.experiments_create(
            'Update state experiment',
            subject.identifier,
            image_group.identifier,
            properties={'comment':'Experiment created automatically to test model run update state'}
        )
        run = experiment.run('Test Run', arguments={'max_eccentricity':11})
        self.assertTrue(run.state.is_idle)
        run = run.update_state_active()
        self.assertTrue(run.state.is_running)
        # Update state to SUCCESS with some fake resut.
        run = run.update_state_success(self.RESULT_FILE)
        self.assertTrue(run.state.is_success)
        # Updating again should raise ValueError
        with self.assertRaises(ValueError):
            run.update_state_success(self.RESULT_FILE)


if __name__ == '__main__':
    # Pass data directory as optional parameter
    if len(sys.argv) == 2:
        DATA_DIR = sys.argv[1]
    sys.argv = sys.argv[:1]
    unittest.main()
