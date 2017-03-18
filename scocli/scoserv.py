"""Collection of methods and definitions related to the Standard Cortical
Observer Web API resources.
"""

import datetime as dt
from dateutil import tz
import json
import os
import requests
import shutil
import tarfile
import tempfile
import urllib2


# ------------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------------

"""HATEOAS reference keys."""

# SCO-API create experiment
REF_EXPERIMENTS_CREATE = 'experiments.create'
# SCO-API experiments listing
REF_EXPERIMENTS_LISTING = 'experiments.list'
# SCO-API list experiments runs
REF_EXPERIMENTS_RUNS_CREATE = 'predictions.run'
# SCO-API list experiments runs
REF_EXPERIMENTS_RUNS_LISTING = 'predictions.list'
# SCO-API create image group
REF_IMAGE_GROUPS_CREATE = 'images.upload'
# SCO-API image groups listing
REF_IMAGE_GROUPS_LIST = 'images.groups.list'
# SCO-API create subject
REF_SUBJECTS_CREATE = 'subjects.upload'
# SCO-API subjects listing
REF_SUBJECTS_LIST = 'subjects.list'
# Resource download
REF_DOWNLOAD = 'download'
# Resource links listing
REF_LINKS = 'links'
# Resource self reference
REF_SELF = 'self'
# Upsert options (currently for image groups only)
REF_UPDATE_OPTIONS = 'options'
# Update model run state
REF_UPDATE_STATE_ACTIVE = 'state.active'
REF_UPDATE_STATE_ERROR = 'state.error'
REF_UPDATE_STATE_SUCCESS = 'state.success'
# Upsert properties reference for resources
REF_UPSERT_PROPERTIES = 'properties'

"""Query parameter for object listings."""

# List of attributes to include for each item in listings
QPARA_ATTRIBUTES = 'properties'
# Limit number of items in result
QPARA_LIMIT = 'limit'
# Set offset in collection
QPARA_OFFSET = 'offset'

"""Model run timestamp keys"""

RUN_CREATED_AT = 'createdAt'
RUN_FINISHED_AT = 'finishedAt'
RUN_STARTED_AT = 'startedAt'

""" Run states """

RUN_FAILED = 'FAILED'
RUN_IDLE = 'IDLE'
RUN_ACTIVE = 'RUNNING'
RUN_SUCCESS = 'SUCCESS'

# ------------------------------------------------------------------------------
#
# SCO Web API Resources
#
# ------------------------------------------------------------------------------

class Attribute(object):
    """Attributes are name value pairs. Attributes are used to represent image
    group options and model run arguments.

    Attributes
    ----------
    name : string
        Property name
    value : any
        Associated value for the property. Can be of any type
    """
    def __init__(self, name, value):
        """Initialize the type property instance by passing arguments for name
        and value.

        Parameters
        ----------
        name : string
            Property name

        value : any
            Associated value for the property. Can be of any type
        """
        self.name = name
        self.value = value


class ResourceHandle(object):
    """Generic handle for a Web API resource in resource listing. Contains the
    four basic resource attributes identifier, name, timestamp, and url. If
    additional properties where requested in the listing call, these will be
    available in a properties dictionary.

    Attributes
    ----------
    identifier : string
        Unique resource identifier
    name : string
        Resource name
    timestamp : datetime.datetime
        Timestamp of resource creation (UTC)
    url : string
        Url to access the resource
    properties : Dictionary
        Dicrionary of additional resource properties and their values. None if
        no additional properties where requested in the client listing method
        call.
    links : Dictionary
        Dictionary of HATEOAS references associated with the resource
    """
    def __init__(self, json_obj):
        """Initialize the resource handle using the Json object for the resource
        in the listing result returned by the Web API.

        Parameters
        ----------
        json_obj : Json object
            Json object for resources as returned by Web API
        """
        # Get resource attributes from the Json object
        self.identifier = json_obj['id']
        self.name = json_obj['name']
        # Convert object's creation timestamp from UTC to local time
        self.timestamp = to_local_time(json_obj['timestamp'])
        # Get resource HATEOAS references
        self.links = references_to_dict(json_obj[REF_LINKS])
        # Get self reference from list of resource links
        self.url = self.links[REF_SELF]
        # Set resource properties if present in the Json object. For handles
        # in object listings the property element will not be present. In that
        # case the local attribute is set to None.
        if 'properties' in json_obj:
            self.properties = {}
            for kvp in json_obj['properties']:
                self.properties[str(kvp['key'])] = str(kvp['value'])
        else:
            self.properties = None


# ------------------------------------------------------------------------------
# Experiments
# ------------------------------------------------------------------------------

class ExperimentHandle(ResourceHandle):
    """Resource handle for SCO experiment resource. Experiments are not directly
    associated with any downloadable data files. However, the experiment refers
    to associated subject and image group resources that are cached on local
    disk.

    Attributes
    ----------
    fmri_url : string
        Url for associated fMRI resource. None if no fMRI is associated with
        this experiment
    image_group_url : string
        Url for associated image group resource.
    runs_url : string
        Url for associated model runs
    subject_url : string
        Url for associated subject resource
    """
    def __init__(self, json_obj, sco):
        """Initialize image group handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        sco : SCOClient
            Client to access associated resources.
        """
        super(ExperimentHandle, self).__init__(json_obj)
        # Maintain reference to SCO client to access subject and image group
        # resources when requested
        self.sco = sco
        # Maintain Urls for associated subject, image group, fMRI, and model
        # run resources
        self.subject_url = references_to_dict(
            json_obj['subject']['links']
        )[REF_SELF]
        self.image_group_url = references_to_dict(
            json_obj['images']['links']
        )[REF_SELF]
        if 'fmri' in json_obj:
            self.fmri_url = references_to_dict(
                json_obj['fmri']['links']
            )[REF_SELF]
        else:
            self.fmri_url = None
        self.runs_url = self.links[REF_EXPERIMENTS_RUNS_LISTING]

    @staticmethod
    def create(url, name, subject_id, image_group_id, properties):
        """Create a new experiment using the given SCO-API create experiment Url.

        Parameters
        ----------
        url : string
            Url to POST experiment create request
        name : string
            User-defined name for experiment
        subject_id : string
            Unique identifier for subject at given SCO-API
        image_group_id : string
            Unique identifier for image group at given SCO-API
        properties : Dictionary
            Set of additional properties for created experiment. Argument may be
            None. Given name will override name property in this set (if present).

        Returns
        -------
        string
            Url of created experiment resource
        """
        # Create list of key,value-pairs representing experiment properties for
        # request. The given name overrides the name in properties (if present).
        obj_props = [{'key':'name','value':name}]
        if not properties is None:
            # Catch TypeErrors if properties is not a list.
            try:
                for key in properties:
                    if key != 'name':
                        obj_props.append({'key':key, 'value':properties[key]})
            except TypeError as ex:
                raise ValueError('invalid property set')
        # Create request body and send POST request to given Url
        body = {
            'subject' : subject_id,
            'images' : image_group_id,
            'properties' : obj_props
        }
        try:
            req = urllib2.Request(url)
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps(body))
        except urllib2.URLError as ex:
            raise ValueError(str(ex))
        # Get experiment self reference from successful response
        return references_to_dict(json.load(response)['links'])[REF_SELF]

    @property
    def image_group(self):
        """Image group resource that is associated with this experiment.

        Returns
        -------
        ImageGroupHandle
            Handle for associated image group resource
        """
        return self.sco.image_groups_get(self.image_group_url)

    def run(self, model_id, name, arguments={}, properties=None):
        """Create a new model run with given name, arguments, and properties.
        Parameters
        ----------
        model_id : string
            Unique model identifier
        name : string
            User-defined name for experiment
        arguments : Dictionary
            Dictionary of arguments for model run
        properties : Dictionary, optional
            Set of additional properties for created mode run.

        Returns
        -------
        scoserv.ModelRunHandle
            Handle for local copy of created model run resource
        """
        return self.sco.experiments_runs_create(
            model_id,
            name,
            self.links[REF_EXPERIMENTS_RUNS_CREATE],
            arguments=arguments,
            properties=properties
        )

    def runs(self, offset=0, limit=-1, properties=None):
        """Get a list of run descriptors associated with this expriment.

        Parameters
        ----------
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
        return get_run_listing(
            self.runs_url,
            offset=offset,
            limit=limit,
            properties=properties
        )

    @property
    def subject(self):
        """Subject resource that is associated with this experiment.

        Returns
        -------
        SubjectHandle
            Handle for associated subject resource
        """
        return self.sco.subjects_get(self.subject_url)


# ------------------------------------------------------------------------------
# Image Groups
# ------------------------------------------------------------------------------

class GroupImage(object):
    """Required for compatibility with the data store image group object.
    Represents an image in a image group.

    Attributes
    ----------
    identifier : string
        Unique identifier of the image
    folder : string
        (Sub-)folder in the grouop (default: /)
    name : string
        Image name (unique within the folder)
    """
    def __init__(self, identifier, folder, name, filename):
        """Initialize attributes of the group image.

        Parameters
        ----------
        identifier : string
            Unique identifier of the image
        folder : string
            (Sub-)folder in the group (default: /)
        name : string
            Image name (unique within the folder)
        filename : string
            Absolute path to file on local disk
        """
        self.identifier = identifier
        self.folder = folder
        self.name = name
        self.filename = filename


class ImageGroupHandle(ResourceHandle):
    """Resource handle for SCO image group resource on local disk. The contents
    of the image group tar-file are extracted into the objects data directory.

    Attributes
    ----------
    data_dir : string
        Absolute path to directory containing a local copy of the resource
        data files
    images : List(string)
        List if absolute file path to images in the group.
    options : Dictionary(Attribute)
        Dictionary of options for image group
    """
    def __init__(self, json_obj, base_dir):
        """Initialize image group handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        base_dir : string
            Path to cache base directory for object
        """
        super(ImageGroupHandle, self).__init__(json_obj)
        # Set image group options
        self.options = {}
        for kvp in json_obj['options']:
            a_name = str(kvp['name'])
            self.options[a_name] = Attribute(a_name, kvp['value'])
        # Set the data directory. If directory does not exist, create it,
        # download the resource data archive, and unpack into data directory
        self.data_directory = os.path.abspath(os.path.join(base_dir, 'data'))
        if not os.path.isdir(self.data_directory):
            os.mkdir(self.data_directory)
            # Download tar-archive
            tmp_file, f_suffix = download_file(self.links[REF_DOWNLOAD])
            # Unpack downloaded file into data directory
            try:
                tf = tarfile.open(name=tmp_file, mode='r')
                tf.extractall(path=self.data_directory)
            except (tarfile.ReadError, IOError) as err:
                # Clean up in case there is an error during extraction
                shutil.rmtree(self.data_directory)
                raise ValueError(str(err))
            # Remove downloaded file
            os.remove(tmp_file)
        # Set list of group images. The list (and order) of images is stored in
        # the .images file in the resource's data directory. If the file does
        # not exists read list from SCO-API.
        self.images = []
        images_file = os.path.join(base_dir, '.images')
        if not os.path.isfile(images_file):
            json_list = JsonResource(
                references_to_dict(
                    json_obj['images']['links']
                )[REF_SELF] + '?' + QPARA_LIMIT + '=-1'
            ).json
            with open(images_file, 'w') as f:
                for element in json_list['items']:
                    # Folder names start with '/'. Remove to get abs local path
                    local_path = element['folder'][1:] + element['name']
                    img_file = os.path.join(self.data_directory, local_path)
                    record = '\t'.join([
                        element['id'],
                        element['folder'],
                        element['name'],
                        local_path
                    ])
                    f.write(record + '\n')
                    self.images.append(
                        GroupImage(
                            element['id'],
                            element['folder'],
                            element['name'],
                            img_file
                        )
                    )
        else:
            # Read content of images file into images list
            with open(images_file, 'r') as f:
                for line in f:
                    tokens = line.strip().split('\t')
                    self.images.append(
                        GroupImage(
                            tokens[0],
                            tokens[1],
                            tokens[2],
                            os.path.join(self.data_directory, tokens[3])
                        )
                    )

    @staticmethod
    def create(url, filename, options, properties):
        """Create new image group at given SCO-API by uploading local file.
        Expects an tar-archive containing images in the image group. Allows to
        update properties of created resource.

        Parameters
        ----------
        url : string
            Url to POST image group create request
        filename : string
            Path to tar-archive on local disk
        options : Dictionary, optional
            Values for image group options. Argument may be None.
        properties : Dictionary
            Set of additional properties for image group (may be None)

        Returns
        -------
        string
            Url of created image group resource
        """
        # Ensure that the file has valid suffix
        if not has_tar_suffix(filename):
            raise ValueError('invalid file suffix: ' + filename)
        # Upload file to create image group. If response is not 201 the uploaded
        # file is not a valid tar file
        files = {'file': open(filename, 'rb')}
        response = requests.post(url, files=files)
        if response.status_code != 201:
            raise ValueError('invalid file: ' + filename)
        # Get image group HATEOAS references from successful response
        links = references_to_dict(response.json()['links'])
        resource_url = links[REF_SELF]
        # Update image group options if given
        if not options is None:
            obj_ops = []
            # Catch TypeErrors if properties is not a list.
            try:
                for opt in options:
                    obj_ops.append({'name' : opt, 'value' : options[opt]})
            except TypeError as ex:
                raise ValueError('invalid option set')
            try:
                req = urllib2.Request(links[REF_UPDATE_OPTIONS])
                req.add_header('Content-Type', 'application/json')
                response = urllib2.urlopen(
                    req,
                    json.dumps({'options' : obj_ops})
                )
            except urllib2.URLError as ex:
                raise ValueError(str(ex))
        # Update image group properties if given
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
# Model Runs
# ------------------------------------------------------------------------------

class ModelRunState(object):
    """Object representing the state of a predictive model run. Contains the
    state name (i.e., textual identifier). Provides flags for individual states
    to simplify test for specific run states.

    Attributes
    ----------
    is_active : Boolean
        True, if run state is 'RUNNING'
    is_failed : Boolean
        True, if run state is 'FAILED'
    is_idle : Boolean
        True, if run state is is_idle
    is_success : Boolean
        True, if run state is success
    name : string
        Run state name
    """
    def __init__(self, state):
        """Initialize the run state with the state identifier.

        Parameters
        ----------
        state : string
            Run state identifier
        """
        # Ensure that state is valid
        if not state in [RUN_ACTIVE, RUN_FAILED, RUN_IDLE, RUN_SUCCESS]:
            raise ValueError('invalid state identifier: ' + str(state))
        # Set state name
        self.name = state

    def __repr__(self):
        """String representation of the run state object."""
        return self.name

    @property
    def is_failed(self):
        """Flag indicating if the model run has exited in a failed state.

        Returns
        -------
        Boolean
            True, if model run is in falied state.
        """
        return self.name == RUN_FAILED

    @property
    def is_idle(self):
        """Flag indicating if the model run is waiting to start execution.

        Returns
        -------
        Boolean
            True, if model run is in idle state.
        """
        return self.name == RUN_IDLE

    @property
    def is_running(self):
        """Flag indicating if the model run is in a running state.

        Returns
        -------
        Boolean
            True, if model run is in running state.
        """
        return self.name == RUN_ACTIVE

    @property
    def is_success(self):
        """Flag indicating if the model run has finished with success.

        Returns
        -------
        Boolean
            True, if model run is in success state.
        """
        return self.name == RUN_SUCCESS


class ModelRunDescriptor(ResourceHandle):
    """Handle for model runs. Extends the default resource handle with
    information about the run state.

    Attributes
    ----------
    state : string
        State of the model run ('FAILED', 'IDLE', 'RUNNING', 'SUCCESS')
    """
    def __init__(self, json_obj):
        """Initialize the run descriptor using the Json object for the model
        run in the listing result returned by the Web API.

        Parameters
        ----------
        json_obj : Json object
            Json object for model run as returned by Web API. Expected to
            contain additional state field.
        """
        super(ModelRunDescriptor, self).__init__(json_obj)
        # Set run state
        self.state = ModelRunState(json_obj['state'])


class ModelRunHandle(ModelRunDescriptor):
    """Resource handle for SCO model run. Contains dictionary of timestamps
    for run scheduling. For failed runs a list of error messages is maintained.
    For completed runs a rference to the result file is maintainted.

    Attributes
    ----------
    arguments : Dictionary(Attribute)
        Dictionary of arguments for the model run
    experiment_url : string
        Url for associated experiment
    model_id : string
        Unique model identifier
    schedule : Dictionary(datetime)
        Dictionary of timestamps for run events
    errors : List(string), Optional
        List of error messages (only for runs in FAILED state)
    result_file : string
        Path to result file (only for runs in SUCCESS state)
    """
    def __init__(self, json_obj, base_dir, sco):
        """Initialize subject handle.
        Parameters
        ----------
        json_obj : Json-like object
            Json object containing resource description
        base_dir : string
            Path to cache base directory for object
        sco : SCOClient
            Client to access associated experiment.
        """
        super(ModelRunHandle, self).__init__(json_obj)
        # Maintain reference to SCO client to access experiment
        self.sco = sco
        # Set model identifier
        self.model_id = json_obj['model']
        # Create list of arguments for model run
        # Set image group options
        self.arguments = {}
        for kvp in json_obj['arguments']:
            a_name = str(kvp['name'])
            self.arguments[a_name] = Attribute(a_name, kvp['value'])
        # Extract experiment Url
        self.experiment_url = references_to_dict(
            json_obj['experiment'][REF_LINKS]
        )[REF_SELF]
        # Create list of schedule timestamps
        self.schedule = {}
        for key in json_obj['schedule']:
            self.schedule[key] = to_local_time(json_obj['schedule'][key])
        # For failed runs create attribute errors containing list of errors
        # messages
        if self.state.is_failed:
            self.errors = json_obj['errors']
        elif self.state.is_success:
            # Name of the result data file
            filename = None
            # Create data directory if it doesnt exist
            data_dir = os.path.abspath(os.path.join(base_dir, 'data'))
            if not os.path.isdir(data_dir):
                os.mkdir(data_dir)
            else:
                # If the directory exists check whether it contains the result
                # data file. The file name is expected to start with the run
                # identifier.
                for f in os.listdir(data_dir):
                    if f.startswith(self.identifier):
                        filename = f
                        break
            # Download the result file if it has not been downloaded yet
            if filename is None:
                tmp_file, f_suffix = download_file(self.links[REF_DOWNLOAD])
                filename = self.identifier + f_suffix
                self.result_file = os.path.join(data_dir, filename)
                shutil.move(tmp_file, self.result_file)
            else:
                self.result_file = os.path.join(data_dir, filename)

    @staticmethod
    def create(url, model_id, name, arguments, properties=None):
        """Create a new model run using the given SCO-API create model run Url.

        Parameters
        ----------
        url : string
            Url to POST model run create model run request
        model_id : string
            Unique model identifier
        name : string
            User-defined name for model run
        arguments : Dictionary
            Dictionary of arguments for model run
        properties : Dictionary, optional
            Set of additional properties for created mode run.

        Returns
        -------
        string
            Url of created model run resource
        """
        # Create list of model run arguments. Catch TypeErrors if arguments is
        # not a list.
        obj_args = []
        try:
            for arg in arguments:
                obj_args.append({'name' : arg, 'value' : arguments[arg]})
        except TypeError as ex:
            raise ValueError('invalid argument set')
        # Create request body and send POST request to given Url
        body = {
            'model' : model_id,
            'name' : name,
            'arguments' : obj_args,
        }
        # Create list of properties if given.  Catch TypeErrors if properties is
        # not a list.
        if not properties is None:
            obj_props = []
            try:
                for key in properties:
                    if key != 'name':
                        obj_props.append({'key':key, 'value':properties[key]})
            except TypeError as ex:
                raise ValueError('invalid property set')
            body['properties'] =  obj_props
        # POST create model run request
        try:
            req = urllib2.Request(url)
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps(body))
        except urllib2.URLError as ex:
            raise ValueError(str(ex))
        # Get model run self reference from successful response
        return references_to_dict(json.load(response)['links'])[REF_SELF]

    @property
    def experiment(self):
        """Experiment resource for which this is a model run.

        Returns
        -------
        ExperimentHandle
            Handle for associated experiment resource
        """
        return self.sco.experiments_get(self.experiment_url)

    def refresh(self):
        """Get a refreshed version of the resource handle. Primarily necessary
        to minitor changes to the run state.

        Note that this handle is not refreshed but a fresh handle is returned!

        Returns
        -------
        ModelRunHandle
            Refreshed run handle.
        """
        return self.sco.experiments_runs_get(self.url)

    @staticmethod
    def update_state(url, state_obj):
        """Update the state of a given model run. The state object is a Json
        representation of the state as created by the SCO-Server.

        Throws a ValueError if the resource is unknown or the update state
        request failed.

        Parameters
        ----------
        url : string
            Url to POST model run create model run request
        state_obj : Json object
            State object serialization as expected by the API.
        """
        # POST update run state request
        try:
            req = urllib2.Request(url)
            req.add_header('Content-Type', 'application/json')
            response = urllib2.urlopen(req, json.dumps(state_obj))
        except urllib2.URLError as ex:
            raise ValueError(str(ex))
        # Throw exception if resource was unknown or update request failed
        if response.code == 400:
            raise ValueError(response.message)
        elif response.code == 404:
            raise ValueError('unknown model run')

    def update_state_active(self):
        """Update the state of the model run to active.

        Raises an exception if update fails or resource is unknown.

        Returns
        -------
        ModelRunHandle
            Refreshed run handle.
        """
        # Update state to active
        self.update_state(self.links[REF_UPDATE_STATE_ACTIVE], {'type' : RUN_ACTIVE})
        # Returned refreshed verion of the handle
        return self.refresh()

    def update_state_error(self, errors):
        """Update the state of the model run to 'FAILED'. Expects a list of
        error messages.

        Raises an exception if update fails or resource is unknown.

        Parameters
        ----------
        errors : List(string)
            List of error messages

        Returns
        -------
        ModelRunHandle
            Refreshed run handle.
        """
        # Update state to active
        self.update_state(
            self.links[REF_UPDATE_STATE_ERROR],
            {'type' : RUN_FAILED, 'errors' : errors}
        )
        # Returned refreshed verion of the handle
        return self.refresh()

    def update_state_success(self, model_output):
        """Update the state of the model run to 'SUCCESS'. Expects a model
        output result file. Will upload the file before changing the model
        run state.

        Raises an exception if update fails or resource is unknown.

        Parameters
        ----------
        model_output : string
            Path to model run output file

        Returns
        -------
        ModelRunHandle
            Refreshed run handle.
        """
        # Upload model output
        response = requests.post(
            self.links[REF_UPDATE_STATE_SUCCESS],
            files={'file': open(model_output, 'rb')}
        )
        if response.status_code != 200:
            try:
                raise ValueError(json.loads(response.text)['message'])
            except ValueError as ex:
                raise ValueError('invalid state change: ' + str(response.text))
        # Returned refreshed verion of the handle
        return self.refresh()


# ------------------------------------------------------------------------------
# Subjects
# ------------------------------------------------------------------------------

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
# Helper Classes
#
# ------------------------------------------------------------------------------

class JsonResource:
    """Simple class to wrap a GET request that reads a Json object. Includes the
    request response and the retrieved Json object.

    Attributes
    ----------
    json : Json object
        Json response object
    response : Response
        Http request response object
    """
    def __init__(self, url):
        """Get Json object from given Url.

        Raises ValueError if given Url cannot be read or result is not a valid
        Json object.

        Parameters
        ----------
        url : string
            Url of resource to be read
        """
        try:
            self.response = urllib2.urlopen(url)
        except urllib2.URLError as ex:
            raise ValueError(str(ex))
        self.json = json.loads(self.response.read())


# ------------------------------------------------------------------------------
#
# Helper Methods
#
# ------------------------------------------------------------------------------

def download_file(url):
    """Download attached file as temporary file.

    Parameters
    ----------
    url : string
        SCO-API downlioad Url

    Returns
    -------
    string, string
        Path to downloaded file and file suffix
    """
    r = urllib2.urlopen(url)
    # Expects a tar-archive or a compressed tar-archive
    if r.info()['content-type'] == 'application/x-tar':
        suffix = '.tar'
    elif r.info()['content-type'] == 'application/gzip':
        suffix = '.tar.gz'
    else:
        raise ValueError('unexpected file type: ' + r.info()['content-type'])
    # Save attached file in temp file and return path to temp file
    fd, f_path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, r.read())
    os.close(fd)
    return f_path, suffix


def get_freesurfer_dir(directory):
    """Test if a directory is a Freesurfer anatomy directory. Currently, the
    test is whether (1) there are sub-folders with name 'surf' and 'mri' and
    (2) if the Freesurfer library method freesurfer_subject returns a non-None
    result for the directory. Processes all sub-folders recursively until a
    freesurfer directory is found. If no matching folder is found the result is
    None.

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


def get_resource_listing(url, offset, limit, properties):
    """Gneric method to retrieve a resource listing from a SCO-API. Takes the
    resource-specific API listing Url as argument.

    Parameters
    ----------
    url : string
        Resource listing Url for a SCO-API
    offset : int, optional
        Starting offset for returned list items
    limit : int, optional
        Limit the number of items in the result
    properties : List(string)
        List of additional object properties to be included for items in
        the result

    Returns
    -------
    List(ResourceHandle)
        List of resource handle (one per subject in the object listing)
    """
    # Create listing query based on given arguments
    query = [
        QPARA_OFFSET + '=' + str(offset),
        QPARA_LIMIT + '=' + str(limit)
    ]
    # Add properties argument if property list is not None and not empty
    if not properties is None:
        if len(properties) > 0:
            query.append(QPARA_ATTRIBUTES + '=' + ','.join(properties))
    # Add query to Url.
    url = url + '?' + '&'.join(query)
    # Get subject listing Url for given SCO-API and decorate it with
    # given listing arguments. Then retrieve listing from SCO-API.
    json_obj = JsonResource(url).json
    # Convert result into a list of resource handles and return the result
    resources = []
    for element in json_obj['items']:
        resource = ResourceHandle(element)
        # Add additional properties to resource if list is given
        if not properties is None:
            resource.properties = {}
            for prop in properties:
                if prop in element:
                    resource.properties[prop] = element[prop]
        resources.append(resource)
    return resources


def get_run_listing(listing_url, offset, limit, properties):
    """Get list of experiment resources from a SCO-API.

    Parameters
    ----------
    listing_url : string
        url for experiments run listing.
    offset : int
        Starting offset for returned list items
    limit : int
        Limit the number of items in the result
    properties : List(string)
        List of additional object properties to be included for items in
        the result

    Returns
    -------
    List(scoserv.ModelRunDescriptor)
        List of model run descriptors
    """
    # Create listing query based on given arguments
    query = [
        QPARA_OFFSET + '=' + str(offset),
        QPARA_LIMIT + '=' + str(limit)
    ]
    # Ensure that the run state is included in the listing as attribute
    props = ['state']
    # Add properties argument if property list is not None and not empty
    if not properties is None:
        for prop in properties:
            if not prop in props:
                props.append(prop)
    query.append(QPARA_ATTRIBUTES + '=' + ','.join(props))
    # Add query to Url.
    url = listing_url + '?' + '&'.join(query)
    # Get subject listing Url for given SCO-API and decorate it with
    # given listing arguments. Then retrieve listing from SCO-API.
    json_obj = JsonResource(url).json
    # Convert result into a list of resource handles and return the result
    resources = []
    for element in json_obj['items']:
        resource = ModelRunDescriptor(element)
        # Add additional properties to resource if list is given
        if not properties is None:
            resource.properties = {}
            for prop in properties:
                if prop in element:
                    resource.properties[prop] = element[prop]
        resources.append(resource)
    return resources


def has_tar_suffix(filename):
    """Check if given filename suffix is a valid tar-file suffix.

    Parameters
    ----------
    filename : string
        Name of file on disk

    Returns
    -------
    Boolean
        True, if filename ends with '.tar', '.tar.gz', or '.tgz'
    """
    for suffix in ['.tar', '.tar.gz', '.tgz']:
        if filename.endswith(suffix):
            return True
    return False


def references_to_dict(elements):
    """Convery a list of HATEOAS reference objects into a dictionary.
    Parameters
    ----------
    elements : List
        List of key value pairs, i.e., [{rel:..., href:...}].
    Returns
    -------
    Dictionary
        Dictionary of rel:href pairs.
    """
    dictionary = {}
    for kvp in elements:
        dictionary[str(kvp['rel'])] = str(kvp['href'])
    return dictionary


def to_local_time(timestamp):
    """Convert a datatime object from UTC time to local time.

    Adopted from:
    http://stackoverflow.com/questions/4770297/python-convert-utc-datetime-string-to-local-datetime

    Parameters
    ----------
    timestamp : string
        Default string representation of timestamps expected to be in
        UTC time zone

    Returns
    -------
    datetime
        Datetime object in local time zone
    """
    utc = dt.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f')
    # Get UTC and local time zone
    from_zone = tz.gettz('UTC')
    to_zone = tz.tzlocal()

    # Tell the utc object that it is in UTC time zone
    utc = utc.replace(tzinfo=from_zone)

    # Convert time zone
    return utc.astimezone(to_zone)
