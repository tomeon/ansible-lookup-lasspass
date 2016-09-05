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
        ''' TODO cache arguments '''
        as_dict         = kwargs.get('as_dict', False)
        basic_regexp    = kwargs.get('basic_regexp', False)
        expand_multi    = kwargs.get('expand_multi', False)
        field           = kwargs.get('field', None)
        fixed_string    = kwargs.get('fixed_string', False)
        pairs           = kwargs.get('merged', False)
        sync            = kwargs.get('sync', None)

        local_args = []

        if sync is not None:
            local_args.append('--sync={0}'.format(sync))

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
        elif fixed_string:
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
            parsed = yaml.safe_load(stdout_io)

            if pairs:
                ret = [dict(key=k.lower(), value=v) for k, v in parsed.iteritems()]
            else:
                ret = {k.lower(): v for k, v in parsed.iteritems()}
        else:
            ret = firstline.rstrip()

        stdout_io.close()

        return ret


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        lp = LastPass()

        status = lp.status()
        display.debug('LASTPASS STATUS {0}'.format(status))

        return [lp.show(term, **kwargs) for term in terms]
