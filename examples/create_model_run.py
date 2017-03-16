"""Create model run for a given experiment. Monitor run state until finished."""

import os
import time

import scocli
import scocli.scoserv as scoserv

# Connect to default SCO-API. Uses a temporary directory to store files in
# local cache
sco = scocli.SCOClient()

experiment = sco.experiments_get('http://localhost:5050/sco-server/api/v1/experiments/a15c4338-de3c-4745-bc98-13fa603e303f')
run = experiment.run('Test Run', arguments={'max_eccentricity':11},properties={'myprop':'useless'})

while not run.state in [scoserv.RUN_FAILED, scoserv.RUN_SUCCESS]:
    if run.state == scoserv.RUN_ACTIVE:
        print run.state + ' (Started @ ' + str(run.schedule[scoserv.RUN_STARTED_AT]) + ')'
    else:
        print run.state
    time.sleep(5)
    run = run.refresh()


print run.identifier
print run.name
print run.state
print run.schedule
print run.arguments
print run.properties
