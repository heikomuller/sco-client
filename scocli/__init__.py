"""Standard Cortical Observer - Web API client

Client to create, access and manipulate resources on Standard Cortical Observer
Web Servers.
"""

import atexit
import json
import logging
import os
import shutil
import tempfile
import uuid

import scoserv as sco
from scoserv import ExperimentHandle, FunctionalDataHandle, ImageGroupHandle
from scoserv import ModelRunHandle, SubjectHandle


# ------------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------------

# Url of default SCO Web API hosted at NYU
DEFAULT_API = 'http://cds-swg1.cims.nyu.edu/sco-server/api/v1'


# ------------------------------------------------------------------------------
#
# Standard Cortical Observer - Client API
#
# ------------------------------------------------------------------------------

class SCOClient(object):
    """Standard Cortical Observer Web API (SCO-API) Client to interact with
    existing SCO-API servers. The client provides access to SCO-API resources
    such as subjects (Anatomy MRI data), image groups, and experiments. It also
    allows to create new resources and to invoke remote model runs

    The client provides access to data files of SCO resources via a local cache.
    The user can specify a folder on disk for the cache to avoid downloading
    files inbetween instantiations of the SCO Client. Alternatively, an new
    temporary directory is used for every instance of the SCO client.
    """
    def __init__(self, api_url=None, data_dir=None):
        """Initialize the client. Provide a default SCO-API Url to use when the
        user calls client methods that list or create resources without giving
        a service base Url. The data directory will be used to cache downloaded
        files permanently. If none is given, a new temporary folder will be
        created. Note that resources in an existing cache folder will not be
        checked for consistency, i.e., they may be deleted on the originating
        server but still be accessible form the local cache. Use cache_clear()
        and cache_clear() and cache_tidy() to remove all cached resources or
        only those that no longer exist on their server.

        Parameters
        ----------
        server_url : string, optional
            Base URL of a SCO Web API. Use to create new resources when no
            API is specified.
        data_dir : string, optional
            Optional directory for caching files. Directory will be created if
            it does not exists. Uses a new temporary directory if no value is
            given by the user.
        """
        # Set the default API Url. This is the API that will be used to create
        # new resources if no API is specified explicitly.
        self.api_url = api_url if not api_url is None else DEFAULT_API
        # Set directory for file cache based on whether argument data_dir is
        # present or not
        if not data_dir is None:
            # Ensure that data_dir refers to a directory. Create the directory
            # if it does not exist
            if os.path.exists(data_dir):
                # Raise error if exsiting path is not a directory
                if not os.path.isdir(data_dir):
                    raise ValueError('not a directory: ' + data_dir)
            else:
                # Create directory if it does not exist
                os.makedirs(data_dir)
            self.directory = data_dir
        else:
            # Use temporary directory as cache directory. Register cleanup
            # handler to remove directory at exit
            self.directory = tempfile.mkdtemp()
            atexit.register(shutil.rmtree, self.directory)
        # The cache index file is a tab delimited file with two columns:
        #
        # 1) resource url
        # 2) unique local cache identifier for resource
        self.db_file = os.path.join(self.directory, 'db.tsv')
        # If the data directory contains a cahce index file (i.e., directory is
        # existing cache directory from previous session) read file content.
        self.cache = {}
        if os.access(self.db_file, os.F_OK):
            with open(self.db_file, 'r') as f:
                for line in f:
                    tokens = line.strip().split('\t')
                    self.cache[tokens[0]] = tokens[1]
        # Set a local cache for SCO API links
        self.apis = {}

    def cache_add(self, resource_url, cache_id):
        """Add entry permanently to local cache.

        Parameters
        ----------
        resource_url : string
            Resource Url
        cache_id : string
            Unique cache identifier for resource
        """
        # Add entry to cache index
        self.cache[resource_url] = cache_id
        # Write cache index content to database file
        with open(self.db_file, 'w') as f:
            for resource in self.cache:
                f.write(resource + '\t' + self.cache[resource] + '\n')

    def cache_clear(self):
        """Clear local cache by deleting all cached resources and their
        downloaded files.
        """
        # Delete content of local cache directory
        for f in os.listdir(self.directory):
            f = os.path.join(self.directory, f)
            if os.path.isfile(f):
                os.remove(f)
            elif os.path.isdir(f):
                shutil.rmtree(f)
        # Empty cache index
        self.cache = {}

    def get_api_references(self, api_url=None):
        """Get set of HATEOAS reference for the given SCO-API. Use the default
        SCO-API if none is given. References are cached as they are not expected
        to change.

        Parameters
        ----------

        Returns
        -------
        """
        # Get subject listing Url for SCO-API
        if not api_url is None:
            url = api_url
        else:
            url = self.api_url
        # Check if API references are in local cache. If not send GET request
        # and add the result to the local cache
        if not url in self.apis:
            self.apis[url] = sco.references_to_dict(
                sco.JsonResource(url).json[sco.REF_LINKS]
            )
        return self.apis[url]

    # --------------------------------------------------------------------------
    # Experiments
    # --------------------------------------------------------------------------

    def experiments_create(self, name, subject_id, image_group_id, api_url=None, properties=None):
        """Create a new experiment at the given SCO-API. Subject and image
        group reference existing resources at the SCO-API.

        Parameters
        ----------
        name : string
            User-defined name for experiment
        subject_id : string
            Unique identifier for subject at given SCO-API
        image_group_id : string
            Unique identifier for image group at given SCO-API
        api_url : string, optional
            Base Url of SCO-API where experiment will be created
        properties : Dictionary, optional
            Set of additional properties for created experiment. The given
            experiment name will override an existing name property in this set.

        Returns
        -------
        scoserv.ExperimentHandle
            Handle for local copy of created experiment resource
        """
        # Create experiment and return handle for created resource
        return self.experiments_get(
            sco.ExperimentHandle.create(
                self.get_api_references(api_url)[sco.REF_EXPERIMENTS_CREATE],
                name,
                subject_id,
                image_group_id,
                properties=properties
            )
        )

    def experiments_get(self, resource_url):
        """Get handle for experiment resource at given Url.

        Parameters
        ----------
        resource_url : string
            Url for experiment resource at SCO-API

        Returns
        -------
        scoserv.ExperimentHandle
            Handle for local copy of experiment resource
        """
        # Get resource directory, Json representation, active flag, and cache id
        obj_dir, obj_json, is_active, cache_id = self.get_object(resource_url)
        # Create experiment handle. Will raise an exception if resource is not
        # in cache and cannot be downloaded.
        experiment = ExperimentHandle(obj_json, self)
        # Add resource to cache if not exists
        if not cache_id in self.cache:
            self.cache_add(resource_url, cache_id)
        # Return experiment handle
        return experiment

    def experiments_list(self, api_url=None, offset=0, limit=-1, properties=None):
        """Get list of experiment resources from a SCO-API.

        Parameters
        ----------
        api_url : string, optional
            Base Url of the SCO-API. Uses default API if argument not present.
        offset : int, optional
            Starting offset for returned list items
        limit : int, optional
            Limit the number of items in the result
        properties : List(string)
            List of additional object properties to be included for items in
            the result

        Returns
        -------
        List(scoserv.ResourceHandle)
            List of resource handles (one per image group in the listing)
        """
        # Get subject listing Url for given SCO-API and return the retrieved
        # resource listing
        return sco.get_resource_listing(
            self.get_api_references(api_url)[sco.REF_EXPERIMENTS_LISTING],
            offset,
            limit,
            properties
        )

    # --------------------------------------------------------------------------
    # Functional Data
    # --------------------------------------------------------------------------

    def experiments_fmri_create(self, experiment_url, data_file):
        """Upload given data file as fMRI for experiment with given Url.

        Parameters
        ----------
        experiment_url : string
            Url for experiment resource
        data_file: Abs. Path to file on disk
            Functional data file

        Returns
        -------
        scoserv.FunctionalDataHandle
            Handle to created fMRI resource
        """
        # Get the experiment
        experiment = self.experiments_get(experiment_url)
        # Upload data
        FunctionalDataHandle.create(
            experiment.links[sco.REF_EXPERIMENTS_FMRI_CREATE],
            data_file
        )
        # Get new fmri data handle and return it
        return self.experiments_get(experiment_url).fmri_data

    def experiments_fmri_get(self, resource_url):
        """Get handle for functional fMRI resource at given Url.

        Parameters
        ----------
        resource_url : string
            Url for fMRI resource at SCO-API

        Returns
        -------
        scoserv.FunctionalDataHandle
            Handle for funcrional MRI data resource
        """
        # Get resource directory, Json representation, active flag, and cache id
        obj_dir, obj_json, is_active, cache_id = self.get_object(resource_url)
        # Create image group handle. Will raise an exception if resource is not
        # in cache and cannot be downloaded.
        fmri_data = FunctionalDataHandle(obj_json, obj_dir)
        # Add resource to cache if not exists
        if not cache_id in self.cache:
            self.cache_add(resource_url, cache_id)
        # Return functional data handle
        return fmri_data

    # --------------------------------------------------------------------------
    # Model Runs
    # --------------------------------------------------------------------------

    def experiments_predictions_create(self, model_id, name, api_url, arguments={}, properties=None):
        """Create a new model run at the given SCO-API.

        Parameters
        ----------
        model_id : string
            Unique model identifier
        name : string
            User-defined name for experiment
        api_url : string
            Url to POST create model run request
        arguments : Dictionary
            Dictionary of arguments for model run
        properties : Dictionary, optional
            Set of additional properties for created mode run.

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of created model run resource
        """
        # Create experiment and return handle for created resource
        return self.experiments_runs_get(
            sco.ModelRunHandle.create(
                api_url,
                model_id,
                name,
                arguments,
                properties=properties
            )
        )

    def experiments_predictions_get(self, resource_url):
        """Get handle for model run resource at given Url.

        Parameters
        ----------
        resource_url : string
            Url for model run resource at SCO-API

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of model run resource
        """
        # Get resource directory, Json representation, active flag, and cache id
        obj_dir, obj_json, is_active, cache_id = self.get_object(resource_url)
        # Create model run handle. Will raise an exception if resource is not
        # in cache and cannot be downloaded.
        run = ModelRunHandle(obj_json, obj_dir, self)
        # Add resource to cache if not exists
        if not cache_id in self.cache:
            self.cache_add(resource_url, cache_id)
        # Return model run handle
        return run

    def experiments_predictions_list(self, listing_url, offset=0, limit=-1, properties=None):
        """Get list of experiment resources from a SCO-API.

        Parameters
        ----------
        listing_url : string
            url for experiments run listing.
        offset : int, optional
            Starting offset for returned list items
        limit : int, optional
            Limit the number of items in the result
        properties : List(string)
            List of additional object properties to be included for items in
            the result

        Returns
        -------
        List(scoserv.ModelRunDescriptor)
            List of model run descriptors
        """
        return sco.get_run_listing(
            listing_url,
            offset=offset,
            limit=limit,
            properties=properties
        )

    def experiments_predictions_update_state_active(self, resource_url):
        """Update state of model run resource at given Url to 'ACTIVE'.

        Parameters
        ----------
        resource_url : string
            Url for model run resource at SCO-API

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of model run resource
        """
        # Send state update request.
        return self.experiments_runs_get(resource_url).update_state_active()

    def experiments_predictions_update_state_error(self, resource_url, errors):
        """Update state of model run resource at given Url to 'FAILED'. Set
        error messages.

        Parameters
        ----------
        resource_url : string
            Url for model run resource at SCO-API
        errors : List(string)
            List of error messages

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of model run resource
        """
        # Send state update request.
        return self.experiments_runs_get(resource_url).update_state_error(
            errors
        )

    def experiments_predictions_update_state_success(self, resource_url, model_output):
        """Update state of model run resource at given Url to 'SUCCESS'. Creates
        a resource for the given model output before updating the model run
        state.

        Parameters
        ----------
        resource_url : string
            Url for model run resource at SCO-API
        model_output : string
            Path to model run output file

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of model run resource
        """
        # Send state update request.
        return self.experiments_runs_get(resource_url).update_state_success(
            model_output
        )


    # --------------------------------------------------------------------------
    # General
    # --------------------------------------------------------------------------

    def get_object(self, resource_url):
        """Get remote resource information. Creates a local directory for the
        resource if this is the first access to the resource. Downloads the
        resource Json representation and writes it into a .json file in the
        cache directory.

        Raises ValueError if resource is not cached and does not exist. If the
        resource no longer exists on the server but in the local cache, a
        reference to the local copy is returned and the value of the is_active
        flag is False.

        Parameters
        ----------
        cache_id : string
            Unique cache identifier
        resource_url : string
            Url of the resource

        Returns
        -------
        (string, Json, Boolean, string)
            Returns a 4-tuple containing local resource directory, the Json
            object representing the resource, an active flag indicating if
            the resource still exists on the remote server or only in the local
            cache, and the resource unique cache identifier.
        """
        # Check if resource is in local cache. If not, create a new cache
        # identifier and set is_cached flag to false
        if resource_url in self.cache:
            cache_id = self.cache[resource_url]
        else:
            cache_id = str(uuid.uuid4())
        # The local cahce directory for resource is given by cache identifier
        obj_dir = os.path.join(self.directory, cache_id)
        # File for local copy of object's Json representation
        f_json = os.path.join(obj_dir, '.json')
        # Object active flag
        is_active = True
        # Read the remote resource representation
        try:
            obj_json = sco.JsonResource(resource_url).json
            # Save local copy of Json object. Create local resource directory if
            # it doesn't exist
            if not os.path.isdir(obj_dir):
                os.mkdir(obj_dir)
            with open(f_json, 'w') as f:
                json.dump(obj_json, f)
        except ValueError as ex:
            # If the resource does not exists but we have a local copy then read
            # object from local disk. Set is_active flag to false. Raise
            # ValueError if no local copy exists
            if os.path.isfile(f_json):
                with open(f_json, 'r') as f:
                    obj_json = json.load(f)
                is_active = False
            else:
                raise ex
        # Return object directory, Json, active flag, and cache identifier
        return obj_dir, obj_json, is_active, cache_id

    # --------------------------------------------------------------------------
    # Image Groups
    # --------------------------------------------------------------------------

    def image_groups_create(self, filename, api_url=None, options=None, properties=None):
        """Create new image group at given SCO-API by uploading local file.
        Expects an tar-archive containing images in the image group. Allows to
        update properties of created resource.

        Parameters
        ----------
        filename : string
            Path to tar-archive on local disk
        api_url : string, optional
            Base Url of SCO-API where image group will be created
        options : Dictionary, optional
            Values for image group options
        properties : Dictionary, optional
            Set of additional properties for created image group

        Returns
        -------
        scoserv.ImageGroupHandle
            Handle for local copy of created image group resource
        """
        # Create image group and return handle for created resource
        return self.image_groups_get(
            sco.ImageGroupHandle.create(
                self.get_api_references(api_url)[sco.REF_IMAGE_GROUPS_CREATE],
                filename,
                options,
                properties
            )
        )

    def image_groups_get(self, resource_url):
        """Get handle for image group resource at given Url.

        Parameters
        ----------
        resource_url : string
            Url for image group resource at SCO-API

        Returns
        -------
        scoserv.ImageGroupHandle
            Handle for local copy of image group resource
        """
        # Get resource directory, Json representation, active flag, and cache id
        obj_dir, obj_json, is_active, cache_id = self.get_object(resource_url)
        # Create image group handle. Will raise an exception if resource is not
        # in cache and cannot be downloaded.
        image_group = ImageGroupHandle(obj_json, obj_dir)
        # Add resource to cache if not exists
        if not cache_id in self.cache:
            self.cache_add(resource_url, cache_id)
        # Return image group handle
        return image_group

    def image_groups_list(self, api_url=None, offset=0, limit=-1, properties=None):
        """Get list of image group resources from a SCO-API.

        Parameters
        ----------
        api_url : string, optional
            Base Url of the SCO-API. Uses default API if argument not present.
        offset : int, optional
            Starting offset for returned list items
        limit : int, optional
            Limit the number of items in the result
        properties : List(string)
            List of additional object properties to be included for items in
            the result

        Returns
        -------
        List(scoserv.ResourceHandle)
            List of resource handles (one per image group in the listing)
        """
        # Get subject listing Url for given SCO-API and return the retrieved
        # resource listing
        return sco.get_resource_listing(
            self.get_api_references(api_url)[sco.REF_IMAGE_GROUPS_LIST],
            offset,
            limit,
            properties
        )

    # --------------------------------------------------------------------------
    # Subjects
    # --------------------------------------------------------------------------

    def subjects_create(self, filename, api_url=None, properties=None):
        """Create new anatomy subject at given SCO-API by uploading local file.
        Expects an tar-archive containing a FreeSurfer anatomy.

        Parameters
        ----------
        filename : string
            Path to tar-archive on local disk
        api_url : string, optional
            Base Url of SCO-API where subject will be created
        properties : Dictionary, optional
            Set of additional properties for created subject

        Returns
        -------
        scoserv.SubjectHandle
            Handle for local copy of created image group resource
        """
        # Create image group and return handle for created resource
        return self.subjects_get(
            sco.SubjectHandle.create(
                self.get_api_references(api_url)[sco.REF_SUBJECTS_CREATE],
                filename,
                properties
            )
        )

    def subjects_get(self, resource_url):
        """Get handle for subject resource at given Url.

        Parameters
        ----------
        resource_url : string
            Url for subject resource at SCO-API

        Returns
        -------
        scoserv.SubjectHandle
            Handle for local copy of subject resource
        """
        # Get resource directory, Json representation, active flag, and cache id
        obj_dir, obj_json, is_active, cache_id = self.get_object(resource_url)
        # Create subject handle. Will raise an exception if resource is not
        # in cache and cannot be downloaded.
        subject = SubjectHandle(obj_json, obj_dir)
        # Add resource to cache if not exists
        if not cache_id in self.cache:
            self.cache_add(resource_url, cache_id)
        # Return subject handle
        return subject

    def subjects_list(self, api_url=None, offset=0, limit=-1, properties=None):
        """Get list of subject resources from a SCO-API.

        Parameters
        ----------
        api_url : string, optional
            Base Url of the SCO-API. Uses default API if argument not present.
        offset : int, optional
            Starting offset for returned list items
        limit : int, optional
            Limit the number of items in the result
        properties : List(string)
            List of additional object properties to be included for items in
            the result

        Returns
        -------
        List(scoserv.ResourceHandle)
            List of resource handles (one per subject in the listing)
        """
        # Get subject listing Url for given SCO-API and return the retrieved
        # resource listing
        return sco.get_resource_listing(
            self.get_api_references(api_url)[sco.REF_SUBJECTS_LIST],
            offset,
            limit,
            properties
        )
