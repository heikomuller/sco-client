"""Standard Cortical Observer - Web API client - Database Resources


Collection of class definitions and methods to represent and manipulate
resources accessible via the Web API.
"""

from abc import abstractmethod
import atexit
import datetime
import os
import shutil
import tempfile
import urllib
import uuid

import urls
import utils


# ------------------------------------------------------------------------------
#
# Web API resources
#
# ------------------------------------------------------------------------------

class ResourceHandle(object):
    """A handle for Web API resources that are associated with a file, e.g,
    subjects or image groups. Provides access to the resource properties and to
    (a local copy of) the file.

    Attributes
    ----------
    identifier : string
        Unique resource identifier
    name : string
        Resource name
    timestamp : datetime
        Timestamp of resource creation
    properties : Dictionary
        Dicrionary of resource properties and their values
    """
    def __init__(self, json_obj, file_manager):
        """Initialize the resource handle using the Json object for the resource
        returned by the Web API.

        Parameters
        ----------
        json_obj : Json object
            Json object for resources as returned by Web API
        file_manager : FileManager
            Instance of file download manager for retrieving files that are
            associated with a resource.
        """
        # Get resource attributes from the Json object
        self.identifier = json_obj['id']
        self.name = json_obj['name']
        self.timestamp = utils.to_local_time(datetime.datetime.strptime(json_obj['timestamp'], '%Y-%m-%dT%H:%M:%S.%f'))
        self.properties = utils.from_list(json_obj['attributes'])
        self.links = utils.from_list(json_obj['links'], label_key='rel', label_value='href')
        # Set the file manager
        self.file_manager = file_manager

    @property
    def file(self):
        """File associated with a resource. Retrieves the file from the Web API
        and returns a file object for it.

        Returns
        -------
        FileObject
            Returns a FileObject if there is a file associated with this
            resource or None.
        """
        # Return the file referenced by a download Url if present.
        if urls.URL_DOWNLOAD in self.links:
            return self.file_manager.get_file(self.links[urls.URL_DOWNLOAD])
        else:
            return None

    @property
    def has_file(self):
        """Flag indicating whether the resource has a downloadable file
        associated with it.

        Returns
        -------
        Boolean
            True, if resource has file associated with it.
        """
        # Downloadable files are indicated by the presence of a download link
        # in the resource's reference list.
        return urls.URL_DOWNLOAD in self.links


# ------------------------------------------------------------------------------
#
# File Manager
#
# ------------------------------------------------------------------------------

class FileManager(object):
    """Abstract file manager class. Provides method to access files that are
    associated with Web API resources.
    """
    @staticmethod
    def download_file(url):
        """Download file referenced by Url to a local location. Return path
        to downloaded file and name of the original file, which might be
        different from the downloaded file name.

        Parameters
        ----------
        url : string
            Url for file resource

        Returns
        -------
        (string, string)
            Tuple of local file name and original file name
        """
        # Retrieve file from Web API into temporary location. The file will
        # not reflect the original file name and siffix, which may be important
        # for some applications.
        local_file, headers = urllib.urlretrieve(url)
        # Extract original file name from header attachement information
        attachments = headers['Content-Disposition']
        file_name = attachments[attachments.find('filename=') + 9:]
        if ';' in file_name:
            file_name = file_name[:file_name.find(';')].strip()
        # Return local file location and original file name
        return local_file, file_name

    @abstractmethod
    def get_file(self, url):
        """Download file at given Url and return file object for it.

        Parameters
        ----------
        url : string
            Url for file resource

        Returns
        -------
        FileObject
            File object for downloaded file
        """
        pass


class DefaultFileManager(FileManager):
    """Default implementation for file manager that does not provide an
    caching of files. Files are downloaded directly using given Url's
    """
    def get_file(self, url):
        """Download file at given Url and return file object for it.

        Parameters
        ----------
        url : string
            Url for file resource

        Returns
        -------
        FileObject
            File object for downloaded file
        """
        # Retrieve file from Web API
        local_file, file_name = self.download_file(url)
        # Copy local file to temp file with file_name.
        temp_dir = tempfile.mkdtemp()
        file_name = os.path.join(temp_dir, file_name)
        os.rename(local_file, file_name)
        # Ensure that tmp_dir is deleted at end of program
        atexit.register(shutil.rmtree, temp_dir)
        return file(file_name)


class DownloadCacheManager(FileManager):
    """Default implementation for file manager that does not provide an
    caching of files. Files are downloaded directly using given Url's
    """
    def __init__(self, data_dir=None):
        # Set the base directory for the file cache. Use ~/.sco if no directory
        # is given.
        if not data_dir is None:
            self.directory = data_dir
        else:
            self.directory = os.path.join(os.path.expanduser("~"), '.sco')
        # Ensure that directory is valid and create it if it doesn't exists
        utils.create_dir(self.directory)
        # The database file is a tab delimited file with two columns:
        #
        # 1) url
        # 2) relative path of downloaded file (relative to directory)
        self.db_file = os.path.join(self.directory, 'db.tsv')
        # Read contents of db file into cache lookup dictionary where downloaded
        # files are keyed by their Url.
        self.cache_lookup = {}
        if os.access(self.db_file, os.F_OK):
            with open(self.db_file, 'r') as f:
                for line in f:
                    tokens = line.strip().split('\t')
                    self.cache_lookup[tokens[0]] = tokens[1]

    def get_file(self, url):
        """Download file at given Url and return file object for it.

        Parameters
        ----------
        url : string
            Url for file resource

        Returns
        -------
        FileObject
            File object for downloaded file
        """
        # Chek if requested file exists in cache. If yes, return file from
        # cache. Otherwise, download file and update cache.
        if url in self.cache_lookup:
            return file(os.path.join(self.directory, self.cache_lookup[url]))
        # Retrieve file from Web API
        local_file, file_name = self.download_file(url)
        # Create new unique sub-folder in the cache directory to store the
        # downloaded file permanently
        file_dir = str(uuid.uuid4())
        os.mkdir(os.path.join(self.directory, file_dir))
        # Relative path for cached file is combination of unique file directory
        # and original file name. Copy the downloaded file to the cache
        # sub-folder.
        relative_file = os.path.join(file_dir, file_name)
        abs_file_name = os.path.join(self.directory, relative_file)
        os.rename(local_file, abs_file_name)
        # Add entry for downloaded file to cache and write db file
        self.cache_lookup[url] = relative_file
        with open(self.db_file, 'w') as f:
            for file_key in self.cache_lookup:
                f.write(file_key + '\t' + self.cache_lookup[file_key] + '\n')
        # Return absolut path to downloaded file in cache directory
        return file(abs_file_name)
