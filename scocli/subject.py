"""Handle for local copy of subject resources."""

import json
import os
import requests
import shutil
import tarfile
import tempfile
import urllib2

from scoserv import ResourceHandle
from scoserv import download_file, has_tar_suffix, references_to_dict
from scoserv import REF_DOWNLOAD, REF_SELF, REF_UPSERT_PROPERTIES


class SubjectHandle(ResourceHandle):
    """Resource handle for SCO subject resource on local disk. Downloads the
    subject tar-file (on first access) and copies the contained FreeSurfer
    directory into the resource's data directory.

    Attributes
    ----------
    data_dir : string
        Absolute path to directory containing the subjects FreeSurfer data files
    """
    def __init__(self, json_obj, base_dir):
        """Initialize subject handle.

        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        base_dir : string
            Path to cache base directory for object
        """
        super(SubjectHandle, self).__init__(json_obj)
        # Set the data directory. If directory does not exist, create it,
        # download the resource data archive, and unpack into data directory
        self.data_directory = os.path.abspath(os.path.join(base_dir, 'data'))
        if not os.path.isdir(self.data_directory):
            # Create data dir and temporary directory to extract downloaded file
            os.mkdir(self.data_directory)
            temp_dir = tempfile.mkdtemp()
            # Download tar-archive and unpack into temp_dir
            tmp_file, f_suffix = download_file(self.links[REF_DOWNLOAD])
            try:
                tf = tarfile.open(name=tmp_file, mode='r')
                tf.extractall(path=temp_dir)
            except (tarfile.ReadError, IOError) as err:
                # Clean up in case there is an error during extraction
                shutil.rmtree(temp_dir)
                shutil.rmtree(self.data_directory)
                raise ValueError(str(err))
            # Remove downloaded file
            os.remove(tmp_file)
            # Make sure the extracted files contain a valid freesurfer directory
            freesurf_dir = get_freesurfer_dir(temp_dir)
            if not freesurf_dir:
                # Clean up before raising an exception
                shutil.rmtree(temp_dir)
                shutil.rmtree(self.data_directory)
                raise ValueError('not a valid subject directory')
            # Move all sub-folders from the Freesurfer directory to the new anatomy
            # data directory
            for f in os.listdir(freesurf_dir):
                sub_folder = os.path.join(freesurf_dir, f)
                if os.path.isdir(sub_folder):
                    shutil.move(sub_folder, self.data_directory)
            # Remove temporary directory
            shutil.rmtree(temp_dir)


    @staticmethod
    def create(url, filename, properties):
        """Create new subject at given SCO-API by uploading local file.
        Expects an tar-archive containing FreeSurfer archive file. Allows to
        update properties of created resource.

        Parameters
        ----------
        url : string
            Url to POST image group create request
        filename : string
            Path to tar-archive on local disk
        properties : Dictionary
            Set of additional properties for subject (may be None)

        Returns
        -------
        string
            Url of created subject resource
        """
        # Ensure that the file has valid suffix
        if not has_tar_suffix(filename):
            raise ValueError('invalid file suffix: ' + filename)
        # Upload file to create subject. If response is not 201 the uploaded
        # file is not a valid FreeSurfer archive
        files = {'file': open(filename, 'rb')}
        response = requests.post(url, files=files)
        if response.status_code != 201:
            raise ValueError('invalid file: ' + filename)
        # Get image group HATEOAS references from successful response
        links = references_to_dict(response.json()['links'])
        resource_url = links[REF_SELF]
        # Update subject properties if given
        if not properties is None:
            obj_props = []
            # Catch TypeErrors if properties is not a list.
            try:
                for key in properties:
                    obj_props.append({'key':key, 'value':properties[key]})
            except TypeError as ex:
                raise ValueError('invalid property set')
            try:
                req = urllib2.Request(links[REF_UPSERT_PROPERTIES])
                req.add_header('Content-Type', 'application/json')
                response = urllib2.urlopen(
                    req,
                    json.dumps({'properties' : obj_props})
                )
            except urllib2.URLError as ex:
                raise ValueError(str(ex))
        return resource_url


# ------------------------------------------------------------------------------
#
# Helper Methods
#
# ------------------------------------------------------------------------------

def get_freesurfer_dir(directory):
    """Find a subfolder in the given directory that contains a Freesurfer
    anatomy (this may be the directory itself). Currently, the test is whether
    there are sub-folders with name 'surf' and 'mri'. Processes all sub-folders
    recursively until a freesurfer directory is found. If no matching folder is
    found the result is None.

    Parameters
    ----------
    directory : string
        Directory on local disk containing unpacked files

    Returns
    -------
    string
        Sub-directory containing a Freesurfer files or None if no such
        directory is found.
    """
    dir_files = [f for f in os.listdir(directory)]
    # Look for sub-folders 'surf' and 'mri'
    if 'surf' in dir_files and 'mri' in dir_files:
        return directory
    # Directory is not a valid freesurfer directory. Continue to search
    # recursively until a matching directory is found.
    for f in os.listdir(directory):
        sub_dir = os.path.join(directory, f)
        if os.path.isdir(sub_dir):
            if get_freesurfer_dir(sub_dir):
                return sub_dir
    # The given directory does not contain a freesurfer anatomy directory
    return None
