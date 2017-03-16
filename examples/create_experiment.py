"""Create experiments for existing subjects and image groups on SCO-API."""

import os

import scocli

# Connect to default SCO-API. Uses a temporary directory to store files in
# local cache
sco = scocli.SCOClient()

# Create an experiment for each combination of subject and image group
# Run sco_calc for each combination of subjects and image groups.
count = 0
for s in sco.subjects_list():
    subject = sco.subjects_get(s.url)
    for ig in sco.image_groups_list():
        image_group = sco.image_groups_get(ig.url)
        experiment = sco.experiments_create(
            'My experiment ' + str(count),
            subject.identifier,
            image_group.identifier,
            properties={'comment':'Experiment created automatically by create_experiment example'}
        )
        count += 1

# List all experiments
print 'EXPERIMENTS:'
print '------------'
for expr in sco.experiments_list(properties=['comment']):
    cols = [expr.identifier, expr.name, str(expr.timestamp)]
    if 'comment' in expr.properties:
        cols.append(expr.properties['comment'])
    print '\t'.join(cols)
