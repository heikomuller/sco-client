# SCO Client API

The client provides access to resources that are managed by SCO Web API's. The client keeps a local cache of resources for faster access. When a resource is first accessed locally it will be downloaded into the local cache. For chached resource we ensure that they are up-to-date whenever they are accessed.

Resources are identfied by their URL.

```
# Create client. Data dir is optional. use ~/.sco if none given. This allows
# to have multiple caches on a local machine
sco = SCOClient()

# Refresh option to enforce new download
subject = sco.subjects_get(url, refresh=False)
images = sco.images_get(url, refresh=False)

opts = images.options

sco_calc(opts, subject=subject.data, stimulation_images=images.files)

# Use existing experiments (primarily to run models on a remote server)

experiment = sco.experiments_get(url)
subject = experiment.subject
images = experiment.images

run = sco.run_experiment(experiment, arguments, name)
sco.run_state(run)

# Clear local cache
sco.clear_cache()

# Create new resources

subject = sco.subjects_create(service_url, freesurfer_archive, name=name)
images = sco.images_create(service_url, tar-file, options, name=name)
experiment = sco.experiments_create(subject, images, arguments, name)
