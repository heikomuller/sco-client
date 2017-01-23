Standard Cortical Observer - Web API Client
===========================================

The SCO Client is a Python library to interact with existing Standard Cortical Observer Web API's (SCO-API). The client provides methods to access resources managed by a SCO-API on a local machine.

The client maintains a local cache for data files that are associated with SCO-API resources (e.g., FreeSurfer anatomy files for a subject). The local cache improves performance by avoiding repeated downloads of remote files. The data files for a resource are not expected to change. Thus, the cached data will always be current. Changeable information associated with a resource, e.g., the user-provided name, is automatically refreshed whenever the resource is accessed locally.


Installation
------------

The easiest way to install the SCO client library is by using `pip install sco-client`. Alternatively, you can clone the library on [GitHub](https://github.com/heikomuller/sco-client)  and run `python setup.py install` in the project home directory.


Usage
-----

Start by creating an instance of the **SCOClient** class.

```
from scocli import SCOClient

sco = SCOClient()
```

The SCOClient has two optional parameter. The first parameter is *api_url* specifying the default SCO-API used by the client instance. Note that the client is not bound to a specific SCO-API. Instead, it allows to access resources managed by different SCO-API's. Respective methods to retrieve and create resources have an (optional) parameter for specifying the SCO-API to use. Only if this parameter is omitted the default SCO-API will be used. By default, the SCOClient will used the [SCO-API at NYU's Center for Data Science](http://cds-swg1.cims.nyu.edu/sco-server/api/v1).

The second parameter, *data_dir*, specifies the directory where data files are cached. If omitted, a new temporary directory will be created for each SCOClient instance. Specifying a data directory has the benefit that one is able to (re-)use cached data between different instantiations of the client. Note that it is not recommended to have multiple programs use the same cache directory in parallel as this may corrupt to local cache.

### List SCO-API resources

The SCO Client allow to list subjects, image groups, and experiments from a SCO-API. The methods thake two optional arguments: the SCO-API and a list of additional properties to include in the listing. These properties are from the list of properties associated with each SCI-API resource. below is an example that lists the identifier, names, timestamp of creation, and name of the uploaded file for each subject at a SCO-API.

```
for subj in sco.subjects_list(properties=['filename']):
    cols = [subj.identifier, subj.name, str(subj.timestamp), subj.properties['filename']]
    print '\t'.join(cols)
```
