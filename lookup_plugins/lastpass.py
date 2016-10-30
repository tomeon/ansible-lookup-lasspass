# (c) 2016, Matt Schreiber <schreibah@gmail.com>
#
# ansible-lookup-lastpass is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import distutils.spawn
import subprocess
import yaml

from StringIO import StringIO

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class LastPass(object):

    NAMED_FIELDS = frozenset(('username', 'password', 'url', 'notes', 'id', 'name',),)

    def __init__(self, command=None):
        if command is not None:
            self.command = command
        else:
            self.command = distutils.spawn.find_executable('lpass')
            if not self.command:
                raise AnsibleError('lpass executable not found in PATH')

    def build_command(self, action, args=[]):
        return [self.command, action, '--color=never'] + args

    def popen_command(self, action, args=[]):
        cmd = self.build_command(action, args=args)

        display.debug('EXEC {0}'.format(' '.join(cmd)))

        return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def run_command(self, action, args=[], in_data=None):
        p = self.popen_command(action, args=args)
        stdout, stderr = p.communicate(in_data)
        return (p.returncode, stdout, stderr)

    def status(self):
        returncode, stdout, stderr = self.run_command('status')

        if returncode != 0:
            raise AnsibleError('lastpass status error: {0}'.format(stdout.rstrip()))

        return stdout.rstrip()

    def show(self, target, **kwargs):
        ''' Show a field or set of fields for a given lpass lookup.
            Corresponds to the ``show`` operation of the ``lpass`` utility.

        :arg target: A :class:`str` to use as the basis of the lookup.
            This must correspond either to the unique ID or unique name
            associated with the LastPass entry.
        :kwarg basic_regexp: When true, indicates that
            :arg target: is to be treated as a regular expression.
        :kwarg fixed_strings: When true, indicates that :arg target: is to
            be treated as a literal string.
        :kwarg expand_multi: If multiple accounts match :arg target:,
            expand the result set for all of them.
        :kwarg field: Which field to retrieve.  Any field associated with
            an account is valid here, so if you have created a custom field for
            an account you may specify it here.  Beware: field names other
            than built-in options (i.e., those that correspond to CLI flags
            like ``--password``) are case-sensitive.  Built-in choices are:

            :username: The ``Username`` field associated with an account.
            :password: The ``Password`` field associated with an account.
            :url: The ``URL`` field associated with an account.
            :notes: The ``notes`` field associated with an account.
            :id: The ID of an account.
            :name: The ``Name`` field associated with an account.
        :kwarg as_dict: Normally, lookups return the content of a single
            field.  When this argument is true, the lookup returns a
            dictionary mapping field names to fields.
        :kwarg pairs: When :kwarg as_dict: is true, returns all fields as a
            list of hashes containing the entries ``key`` and ``value``,
            much like the ``with_dict`` loop type.
        :kwarg sync: Options are:
            :auto:
            :now:
            :no:
            However, no validation is performed.
        :raises AnsibleError: if ``all`` is given for :kwarg field:.  Users
            should instead use the ``as_dict`` option.
        :raises AnsibleError: if the user specified neither a value for
            :kwarg field: nor :kwarg as_dict:.
        :raises AnsibleError: if no data could be retrieved from LastPass. The
            typical reason is that the provided query matches no accounts.
        :raises AnsibleError: if the provided query matches more than one
            account.

        :returns: either the content of a single field, a dictionary mapping
            field names to values if :kwarg as_dict: is true, or a list of
            dictionaries if :kwarg as_dict: and :kwarg pairs: are both true.
        '''

        basic_regexp    = kwargs.get('basic_regexp', False)
        fixed_strings   = kwargs.get('fixed_strings', False)
        expand_multi    = kwargs.get('expand_multi', False)
        field           = kwargs.get('field', None)
        as_dict         = kwargs.get('as_dict', False)
        pairs           = kwargs.get('pairs', False)
        sync            = kwargs.get('sync', None)

        local_args = []

        if sync is not None:
            local_args.append('--sync={0}'.format(sync))

        # TODO this breaks multiple-match-detection logic
        if expand_multi:
            local_args.append('--expand-multi')

        if as_dict:
            local_args.append('--all')
        elif field is not None:
            if field == 'all':
                raise AnsibleError("Use as_dict=True instead of field='all'")

            if field in self.NAMED_FIELDS:
                local_args.append('--{0}'.format(field))
            else:
                local_args.append('--field={0}'.format(field))
        else:
            raise AnsibleError("Please provide a value for field= or use as_dict=True")

        if basic_regexp:
            local_args.append('--basic-regexp')
        elif fixed_strings:
            local_args.append('--fixed-strings')

        local_args.append(target)

        returncode, stdout, stderr = self.run_command('show', local_args)

        if returncode != 0:
            raise AnsibleError('lastpass error retrieving data for {0}: {1}'.format(target, stderr.rstrip()))

        stdout_io = StringIO(stdout)
        firstline = stdout_io.readline()

        if firstline.startswith('Multiple matches'):
            raise AnsibleError('lastpass found multiple matches for {0}'.format(target))
        elif as_dict:
            parsed = self.load_data(stdout_io)

            if pairs:
                print("USING PAIRS!")
                ret = [dict(key=k.lower(), value=v) for k, v in parsed.iteritems()]
            else:
                ret = dict([(k.lower(), v) for k, v in parsed.iteritems()])
        else:
            ret = firstline.rstrip()

        stdout_io.close()

        return ret

    def load_data(self, stream):
        ''' This is a cheap hack until lpass implements output formatting.
            See https://github.com/lastpass/lastpass-cli/issues/192 for
            progress.
        '''
        def format_line(line):
            (k, v) = line.rstrip().split(':', 1)
            return (k, v.strip())

        return dict(map(format_line, stream.readlines()))

class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        lp = LastPass()

        status = lp.status()
        display.debug('LASTPASS STATUS {0}'.format(status))

        return [lp.show(term, **kwargs) for term in terms]
