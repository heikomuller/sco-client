"""Handles for functional data resources."""

import os
import requests
import shutil

from scoserv import ResourceHandle
from scoserv import download_file, references_to_dict
from scoserv import PROPERTY_FUNCDATAFILE
from scoserv import REF_DOWNLOAD, REF_SELF


class FunctionalDataHandle(ResourceHandle):
    """Resource handle for SCO functional data resource on local disk. Downloads
    the functional data tar-file (on first access) and copies the contained
    files into the resource's data directory.

    Attributes
    ----------
    data_directory : string
        (Absolute) Path to directory containing unpacked data files
    data_file : string
	   (Absolute) Path to main functional data file.
    """
    def __init__(self, json_obj, base_dir):
        """Initialize functional data handle.

        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        base_dir : string
            Path to cache base directory for object
        """
        super(FunctionalDataHandle, self).__init__(json_obj)
        # Set the data directory. If directory does not exist, create it.
        # Download the data file into the data directory.
        self.data_directory = os.path.abspath(os.path.join(base_dir, 'data'))
        self.data_file = os.path.join(
            self.data_directory,
            self.properties[PROPERTY_FUNCDATAFILE]
        )
        if not os.path.isdir(self.data_directory):
            os.mkdir(self.data_directory)
            # Download tar-archive and unpack into data_dir
            tmp_file, f_suffix = download_file(self.links[REF_DOWNLOAD])
            # Move the downloaded file to the data directory
            shutil.move(tmp_file, self.data_file)

    @staticmethod
    def create(url, filename):
        """Create new fMRI for given experiment by uploading local file.
        Expects an tar-archive.

        Parameters
        ----------
        url : string
            Url to POST fMRI create request
        filename : string
            Path to tar-archive on local disk

        Returns
        -------
        string
            Url of created functional data resource
        """
        # Upload file to create fMRI resource. If response is not 201 the
        # uploaded file is not a valid functional data archive
        files = {'file': open(filename, 'rb')}
        response = requests.post(url, files=files)
        if response.status_code != 201:
            raise ValueError('invalid file: ' + filename)
            return references_to_dict(response.json()['links'])[REF_SELF]        # Return HATEOAS self references from successful response
