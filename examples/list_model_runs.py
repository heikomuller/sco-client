"""List model runs for all experiments in the API."""

import os

import scocli
import scocli.scoserv as scoserv

# Connect to default SCO-API. Uses a temporary directory to store files in
# local cache
sco = scocli.SCOClient()

# Get experiment object from API
for exp in sco.experiments_list():
    experiment = sco.experiments_get(exp.url)
    # Get model runs for experiment
    for r in experiment.runs():
        run = sco.experiments_runs_get(r.url)
        print '#RUN'
        print 'ID         : ' + run.identifier
        print 'NAME       : ' + run.name
        print 'STATE      : ' + run.state
        print 'EXPERIMENT : ' + run.experiment.identifier
        print 'STARTED AT : ' + str(run.schedule[scoserv.RUN_STARTED_AT])
        if run.state == scoserv.RUN_SUCCESS:
            print 'FINISHED AT: ' + str(run.schedule[scoserv.RUN_FINISHED_AT])
            print 'RESULT     : ' + run.result_file
        elif run.state == scoserv.RUN_FAILED:
            print 'FINISHED AT: ' + str(run.schedule[scoserv.RUN_FINISHED_AT])
            print 'ERRORS     :'
            for err in run.errors:
                print '\t' + str(err)
