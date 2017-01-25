Standard Cortical Observer - Web API Client
===========================================

The SCO Client is a Python library to interact with existing Standard Cortical Observer Web API's (SCO-API). The client provides methods to access resources managed by a SCO-API on a local machine.

The client maintains a local cache for data files that are associated with SCO-API resources (e.g., FreeSurfer anatomy files for a subject). The local cache improves performance by avoiding repeated downloads of remote files. The data files for a resource are not expected to change. Thus, the cached data will always be current. Changeable information associated with a resource, e.g., the user-provided name, is automatically refreshed whenever the resource is accessed locally.


Installation
------------

The easiest way to install the SCO client library is by using `pip install sco-client`. Alternatively, you can clone the library on [GitHub](https://github.com/heikomuller/sco-client)  and run `python setup.py install` in the project home directory.


Usage
-----

The following outlines possible usage of the SCO Client based on short examples. Start by creating an instance of the **SCOClient** class.

```
from scocli import SCOClient

sco = SCOClient()
```

The SCO Client has two optional parameter. The first parameter *api_url* specifies the default SCO-API used by the client instance. Note that a client instance is not bound to a specific SCO-API. Instead, a client can access resources managed by different SCO-API's. Respective client methods to retrieve and create resources have an (optional) parameter for specifying the SCO-API to use. Only if this parameter is omitted the default SCO-API will be used. By default, the SCO Client will used the [SCO-API at NYU's Center for Data Science](http://cds-swg1.cims.nyu.edu/sco-server/api/v1).

The second parameter *data_dir* specifies the directory where data files are cached. If omitted, a new temporary directory is created for each SCO Client instance. Specifying a data directory has the benefit that one is able to (re-)use cached data files between different instantiations of the client. Note that it is not recommended to have multiple programs use the same cache directory in parallel as this may corrupt to local cache.


### List Objects

The SCO Client allows to list subjects, image groups, and experiments from an SCO-API. The respective list methods have two optional parameters: the URL of the SCO-API and a list of additional properties to include for items in the listing result. These properties correspond to properties  in the list of properties associated with each SCO-API resource. Below is an example that lists the identifier, name, timestamp of creation, and name of the uploaded file for each subject managed by the default SCO-API.

```
# Print headline
print '\t'.join(['ID', 'Name', 'Created at', 'Created from file'])
# List all subjects on SCO-API together with the name of the file they were created from
for subj in sco.subjects_list(properties=['filename']):
    # Print subject's properties
    cols = [subj.identifier, subj.name, str(subj.timestamp), subj.properties['filename']]
    print '\t'.join(cols)
```


### Get Objects

The SCO Client provides access to subjects, image groups, and experiments managed by an SCO-API. For subjects and image groups associated data files are downloaded and cached on local file system. The SCO Client creates handles for objects that contain references to data files, e.g., to run a SCO predictive model locally using data from a SCO-API. Below is an example that lists the image files for each image group managed by the default SCO-API.

```
# List all image group on default SCO-API
for item in sco.image_groups_list():
    # Get handle for local copy of image group
    image_group = sco.image_groups_get(item.url)
    print image_group.name
    # List files in image group. image_group.images is a list of local file names.
    for filename in image_group.images:
        print '\t' + filename

```


### Create Objects

The SCO Client allows to create subjects, image groups, and experiments at an SCO-API. Subjects and image groups are created by uploading respective FreeSurefer archives or archive files containing JPEG, GIF, and PNG images. The example below shows how to create objects using the SCO Client.

```
#  Upload FreeSurfer archive
subj = sco.subjects_create('./subject.tar.gz', properties={'name':'Example Subject'})
# Uplaod image archive. For image groups several options can be set
imges = sco.image_groups(
	'images.tar', 
 	options={
		'stimulus_pixels_per_degree' : 1,
		'stimulus_edge_value' : 0.9
  	},
	properties={'comment':'Just an example'}
)
# New experiment based on uploaded subject and image group
expr = sco.experiments_create('My Experiment', subj.identifier, images.identifier)

```