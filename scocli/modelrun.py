"""Handle for local copies of model run resources."""

import json
import os
import requests
import shutil
import urllib2

from scoserv import Attribute, ResourceHandle
from scoserv import download_file, references_to_dict, to_local_time
from scoserv import REF_DOWNLOAD, REF_LINKS, REF_MODEL_RUN_ATTACHMENTS, REF_SELF
from scoserv import REF_UPDATE_STATE_ACTIVE, REF_UPDATE_STATE_ERROR
from scoserv import REF_UPDATE_STATE_SUCCESS


# ------------------------------------------------------------------------------
#
# Constants
#
# ------------------------------------------------------------------------------

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
# Classes
#
# ------------------------------------------------------------------------------

class Attachment(object):
    """Descriptor for model run attachment.

    Attributes
    ----------
    identifier : string
        Unique attachment identifier
    mime_type : string
        File Mime type
    url : string
        Download Url
    """
    def __init__(self, identifier, mime_type, url):
        """Initialize local variables.

        Parameters
        ----------
        identifier : string
            Unique attachment identifier
        mime_type : string
            File Mime type
        url : string
            Download Url
        """
        self.identifier = identifier
        self.mime_type = mime_type
        self.url = url

    def download(self, filename=None):
        """Download an attachment. The files are currently not cached since they
        can be overwritten on the server.

        Parameters
        ----------
        filename : string, optional
            Optional name for the file on local disk.

        Returns
        -------
        string
            Path to downloaded temporary file on disk
        """
        tmp_file, f_suffix = download_file(self.url)
        if not filename is None:
            shutil.move(tmp_file, filename)
            return filename
        else:
            return tmp_file


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
    attachments : list(Attachment)
        List of model run attachments
    data_dir : string
        Path to directory that contains attachements and prediction results
    experiment_url : string
        Url for associated experiment
    model_url : string
        Url for model definition
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
        self.model_url = references_to_dict(
            json_obj['model'][REF_LINKS]
        )[REF_SELF]
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
        # Create data directory if it doesnt exist
        self.data_dir = os.path.abspath(os.path.join(base_dir, 'data'))
        # For failed runs create attribute errors containing list of errors
        # messages
        if self.state.is_failed:
            self.errors = json_obj['errors']
        elif self.state.is_success:
            # Name of the result data file
            filename = json_obj['model']['outputs']['prediction']
            if not os.path.isdir(self.data_dir):
                os.mkdir(self.data_dir)
            self.result_file = os.path.join(self.data_dir, filename)
            # Download the result file if it has not been downloaded yet
            if not os.access(self.result_file, os.F_OK):
                tmp_file, f_suffix = download_file(self.links[REF_DOWNLOAD])
                filename = self.identifier + f_suffix
                shutil.move(tmp_file, self.result_file)
            self.attachments = [
                Attachment(
                    doc['id'],
                    doc['mimeType'],
                    references_to_dict(doc[REF_LINKS])[REF_DOWNLOAD]
                ) for doc in json_obj['attachments']]

    def attach_file(self, filename, resource_id=None):
        """Upload an attachment for the model run.

        Paramerers
        ----------
        filename : string
            Path to uploaded file

        resource_id : string
            Identifier of the attachment. If None, the filename will be used as
            resource identifier.

        Returns
        -------
        ModelRunHandle
            Refreshed run handle.
        """
        # Use file base name as resource identifier if none given
        if resource_id is None:
            resource_id = os.path.basename(filename)
        # Need to append resource identifier to base attachment Url
        upload_url = self.links[REF_MODEL_RUN_ATTACHMENTS] + '/' + resource_id
        # Upload model output
        response = requests.post(
            upload_url,
            files={'file': open(filename, 'rb')}
        )
        if response.status_code != 200:
            try:
                raise ValueError(json.loads(response.text)['message'])
            except KeyError as ex:
                raise ValueError('invalid state change: ' + str(response.text))
        # Returned refreshed verion of the handle
        return self.refresh()

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

    @property
    def model(self):
        """Resource for definition of model that is being run.

        Returns
        -------
        ModelHandle
            Handle for associated model resource
        """
        return self.sco.models_get(self.model_url)

    def refresh(self):
        """Get a refreshed version of the resource handle. Primarily necessary
        to minitor changes to the run state.

        Note that this handle is not refreshed but a fresh handle is returned!

        Returns
        -------
        ModelRunHandle
            Refreshed run handle.
        """
        return self.sco.experiments_predictions_get(self.url)

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
