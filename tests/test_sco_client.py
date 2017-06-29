import os
import sys
import unittest

import scocli

API_URL = 'http://localhost:5000/sco-server/api/v1'
DATA_DIR = './data'

class TestSCOClient(unittest.TestCase):

    def setUp(self):
        """Initialize the SCO Client. Assumes that defautl Web API is active."""
        self.SUBJECT_FILE = os.path.join(DATA_DIR, 'subjects/kay2008_subj1.tar.gz')
        self.IMAGES_FILE = os.path.join(DATA_DIR, 'images/sample_images.tar.gz')
        self.FMRI_FILE = os.path.join(DATA_DIR, 'fmris/sample.nii.gz')
        self.PREDICTION_FILE = os.path.join(DATA_DIR, 'prediction.nii.gz')
        self.sco = scocli.SCOClient(api_url=API_URL, data_dir=DATA_DIR + '/sco')

    def test_create_experiment_with_functional_data(self):
        """Create experiment and assign functional data."""
        # Create subject
        subject = self.sco.subjects_create(
            self.SUBJECT_FILE,
            properties={'name' : 'Kay - Subject 1'}
        )
        # Ensure that subfolders 'mri' and 'surf' exist in the subject's data
        # directory
        self.assertTrue(os.path.isdir(os.path.join(subject.data_directory, 'mri')))
        self.assertTrue(os.path.isdir(os.path.join(subject.data_directory, 'surf')))
        # Create image group
        image_group = self.sco.image_groups_create(
            self.IMAGES_FILE,
            options={
                'pixels_per_degree' : 6
            },
            properties={'name' : 'AutoUploadImages'}
        )
        # Ensure that the data directory for the image group contains 10 files
        for i in range(10):
            self.assertTrue(
                os.path.isfile(
                    os.path.join(
                        image_group.data_directory,
                        'validate_000' + str(i) + '.png'
                    )
                )
            )
        # Ensure that all imgae group data files exist
        for img in image_group.images:
            self.assertTrue(os.path.isfile(img.data_file))
        # Create experiment
        experiment = self.sco.experiments_create(
            'Name',
            subject.identifier,
            image_group.identifier
        )
        # Upload fMRI file for experiment
        self.sco.experiments_fmri_create(
            experiment.url,
            self.FMRI_FILE
        )
        # Get the experiment and ansure that the associated fmri data has two
        # files
        experiment = self.sco.experiments_get(experiment.url)
        fmri = experiment.fmri_data
        # Ensure that the fMRI data file exists on local disk
        self.assertTrue(os.path.isfile(fmri.data_file))
        # Create a new model run
        run = experiment.run('benson17', 'Fake Run', {'max_eccentricity':10.0})
        self.assertEquals(run.state, 'IDLE')
        run = run.update_state_active()
        self.assertEquals(run.state, 'RUNNING')
        with self.assertRaises(ValueError):
            run = run.update_state_active()
        run = run.update_state_success(self.PREDICTION_FILE)
        self.assertEquals(run.state, 'SUCCESS')
        with self.assertRaises(ValueError):
            run.update_state_active()
        with self.assertRaises(ValueError):
            run.update_state_error(['No error'])
        with self.assertRaises(ValueError):
            run.update_state_success(self.PREDICTION_FILE)

    def test_create_experiment_with_missing_references(self):
        """Create experiment with incorrect subject and image group references.
        Ensure that exceptions are thrown as expected."""
        with self.assertRaises(ValueError):
            self.sco.experiments_create('Name', 'A', 'B')
        with self.assertRaises(ValueError):
            self.sco.experiments_create('Name', 'A', 'B', properties='B')

    def test_create_image_group_with_invalid_file(self):
        """Create image group from file with invalid suffix."""
        with self.assertRaises(ValueError):
            self.sco.image_groups_create('Name.txt')
        with self.assertRaises(ValueError):
            self.sco.image_groups_create(
                os.path.join(DATA_DIR, 'not-a-valid-tar-file.tar')
            )

    def test_create_image_group_with_invalid_options(self):
        """Create image group with an invalid set of options."""
        with self.assertRaises(ValueError):
            self.sco.image_groups_create(
                self.IMAGES_FILE,
                options={'no-op' : 0}
            )

    def test_create_image_group_with_invalid_properties(self):
        """Create image group with an invalid set of properties."""
        with self.assertRaises(ValueError):
            self.sco.image_groups_create(
                self.IMAGES_FILE,
                properties={'filename' : 'Some Name'}
            )


if __name__ == '__main__':
    # Pass data directory as optional parameter
    if len(sys.argv) == 2:
        DATA_DIR = sys.argv[1]
    sys.argv = sys.argv[:1]
    unittest.main()
