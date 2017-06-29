from scocli import SCOClient
from scocli.cli import SCOCmdLine, SCOCmdSyntaxError

cmd = SCOCmdLine(SCOClient())

while True:
    try:
        user_input = raw_input("-> ")
    except EOFError as ex:
        break
    if user_input.strip() == '':
        continue
    try:
        for line in cmd.eval(user_input):
            print line
    except SCOCmdSyntaxError as ex:
        print 'ERROR: ' + ex.message

print 'Bye'
