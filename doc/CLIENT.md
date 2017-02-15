# SCO Client API

The SCO client provides access to resources that are managed by SCO Web API's. Each client instance can access resources from multiple API's, i.e., the client is not bound to a particular API instance.

SCO clients keep a local cache of resources for faster access. When a resource is first accessed locally it will be downloaded and added to the local cache. The cached resource are ensured to be up-to-date whenever they are accessed.

## Client API

The SCO Client has the following methods:

### Cache
def cache_clear(self):

### Experiments
experiments_create(self, name, subject_id, image_group_id, api_url=None, properties=None)
experiments_get(self, resource_url):
experiments_list(self, api_url=None, offset=0, limit=-1, properties=None):

experiments_runs_create(name, experiment_id, options=None, properties=None)
experiments_runs_get
experiments_runs_list

### Image Groups
image_groups_create(self, filename, api_url=None, options=None, properties=None):
image_groups_get(self, resource_url):
image_groups_list(self, api_url=None, offset=0, limit=-1, properties=None):

### Subjects
subjects_create(self, filename, api_url=None, properties=None):
subjects_get(self, resource_url):
subjects_list(self, api_url=None, offset=0, limit=-1, properties=None):
