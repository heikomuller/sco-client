import os
import sys
import unittest

import scocli

API_URL = 'http://localhost:5000/sco-server/api/v1'
DATA_DIR = './data'

class TestSCOClient(unittest.TestCase):

    def setUp(self):
        """Initialize the SCO Client. Assumes that defautl Web API is active."""
        self.sco = scocli.SCOClient(api_url=API_URL)

    def test_create_experiment_with_functional_data(self):
        """Create experiment and assign functional data."""
        # Create subject
        subject = self.sco.subjects_create(
            os.path.join(DATA_DIR, 'subjects/ernie.tar.gz'),
            properties={'name' : 'Ernie'}
        )
        # Create image group
        image_group = self.sco.image_groups_create(
            os.path.join(DATA_DIR, 'images/images.tar.gz'),
            options={
                'pixels_per_degree' : 1,
                'aperture_edge_width' : 0.9
            },
            properties={'name' : 'AutoUploadImages'}
        )
        # Create experiment
        experiment = self.sco.experiments_create(
            'Name',
            subject.identifier,
            image_group.identifier
        )
        # Upload fMRI file for experiment
        self.sco.experiments_fmri_create(
            experiment.url,
            os.path.join(DATA_DIR, 'fmris/fmri.tar')
        )
        # Get the experiment and ansure that the associated fmri data has two
        # files
        experiment = self.sco.experiments_get(experiment.url)
        fmri = experiment.fmri_data
        self.assertEquals(len(fmri.data_files), 2)

    def test_create_experiment_with_missing_references(self):
        """Create experiment with incorrect subject and image group references.
        Ensure that exceptions are thrown as expected."""
        with self.assertRaises(ValueError):
            self.sco.experiments_create('Name', 'A', 'B')
        with self.assertRaises(ValueError):
            self.sco.experiments_create('Name', 'A', 'B', properties='B')

    def test_create_image_group(self):
        """Ensure that create image groups works correctly."""
        image_group = self.sco.image_groups_create(
            os.path.join(DATA_DIR, 'images/images.tar.gz'),
            options={
                'pixels_per_degree' : 1,
                'aperture_edge_width' : 0.9
            },
            properties={'name' : 'AutoUploadImages'}
        )
        self.assertIsNotNone(image_group)
        self.assertEqual(image_group.options['aperture_edge_width'].value, 0.9)
        self.assertEqual(image_group.name, 'AutoUploadImages')

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
                os.path.join(DATA_DIR, 'images/images.tar.gz'),
                options={'no-op' : 0}
            )

    def test_create_image_group_with_invalid_properties(self):
        """Create image group with an invalid set of properties."""
        with self.assertRaises(ValueError):
            self.sco.image_groups_create(
                os.path.join(DATA_DIR, 'images/images.tar.gz'),
                properties={'filename' : 'Some Name'}
            )

    def test_create_subject(self):
        """Ensure that create subject works."""
        subject = self.sco.subjects_create(
            os.path.join(DATA_DIR, 'subjects/ernie.tar.gz'),
            properties={'name' : 'Ernie'}
        )
        self.assertIsNotNone(subject)
        self.assertEqual(subject.name, 'Ernie')

    def test_invalid_urls(self):
        """Test SCO client behaviour when given invalid Urls."""
        cli = scocli.SCOClient(api_url='not-an-url')
        with self.assertRaises(ValueError):
            cli.subjects_list()
        with self.assertRaises(ValueError):
            cli.subjects_list(api_url='not-an-url')
        cli = scocli.SCOClient(api_url='http://www.spiegel.de')
        with self.assertRaises(ValueError):
            cli.subjects_list(api_url='http://www.spiegel.de')


if __name__ == '__main__':
    # Pass data directory as optional parameter
    if len(sys.argv) == 2:
        DATA_DIR = sys.argv[1]
    sys.argv = sys.argv[:1]
    unittest.main()
