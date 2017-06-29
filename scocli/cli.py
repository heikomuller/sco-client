"""SCO Client - Command Line Interface - Simple command line tool to interact
with a SCO Web API via the SCO Client.
"""


class SCOCmdLine(object):
    def __init__(self, sco):
        """Initialize the SCO Client that is used too communicate with the
        Web API.

        Parameters
        ----------
        sco : scocli.SCOClient
            SCO client instance
        """
        self.sco = sco

    def eval(self, cmd):
        """Evaluate a given command. The command is parsed and the output
        returned as a list of lines (strings).

        Raises a SCOCmdSyntaxError in case the command cannot be parsed.

        Parameters
        ----------
        cmd : strings
            Command string

        Returns
        -------
        list(stirng)
            Command output as list of strings (lines)
        """
        tokens = cmd.upper().split()
        if len(tokens) == 2 and tokens[0] == 'LIST':
            if tokens[1] == 'EXPERIMENTS':
                return self.list_objects(self.sco.experiments_list())
            elif tokens[1] == 'IMAGES':
                return self.list_objects(self.sco.image_groups_list())
            elif tokens[1] == 'MODELS':
                return self.list_objects(self.sco.models_list())
            elif tokens[1] == 'SUBJECTS':
                return self.list_objects(self.sco.subjects_list())
            else:
                raise SCOCmdSyntaxError(cmd, 'unknown type: ' + cmd.split()[1])
        else:
            raise SCOCmdSyntaxError(cmd, 'unknown command')

    def list_objects(self, resources):
        """Generate a listing for a set of resource handles consisting of
        resource identifier, name, and timestamp.

        Parameters
        ----------
        resources : list(ResourceHandle)
            List of resource handles

        Returns
        -------
        list(string)
        """
        result = []
        for res in resources:
            result.append('\t'.join([res.identifier, res.name, str(res.timestamp)[:19]]))
        return result


# ------------------------------------------------------------------------------
# Exceptions
# ------------------------------------------------------------------------------

class SCOCmdSyntaxError(Exception):
    """Base class for SCO command line parser exceptions."""
    def __init__(self, cmd, message):
        """Initialize command and error message.

        Parameters
        ----------
        cmd : strings
            Command string
        message : string
            Error message.
        """
        Exception.__init__(self)
        self.cmd = cmd
        self.message = message

    def to_dict(self):
        """Dictionary representation of the exception.

        Returns
        -------
        Dictionary
        """
        return {'cmd': self.cmd, 'message' : self.message}
