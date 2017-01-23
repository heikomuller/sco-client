import os
import sys
import unittest

sys.path.insert(0, os.path.abspath('..'))

import scocli


class TestSCOClient(unittest.TestCase):

    def setUp(self):
        """Initialize the SCO Client. Assumes that defautl Web API is active."""
        self.sco = scocli.SCOClient()

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
    unittest.main()
