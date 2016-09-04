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

from ansible.errors import AnsibleError
from ansible.plugins.lookup import LookupBase

try:
    from __main__ import display
except ImportError:
    from ansible.utils.display import Display
    display = Display()


class LastPass(object):

    NAMED_FIELDS = frozenset(('all', 'username', 'password', 'url', 'notes',
                             'id', 'name',),)

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

        display.vvv('EXEC {0}'.format(' '.join(cmd)))

        return subprocess.Popen(cmd, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def run_command(self, action, args=[], in_data=None):
        p = self.popen_command(action, args=args)
        stdout, stderr = p.communicate(in_data)
        return (p.returncode, stdout, stderr)

    def status(self):
        return self.run_command('status')

    def show(self, target, **kwargs):
        ''' TODO cache arguments '''
        local_args = []

        sync = kwargs.get('sync', None)
        if sync is not None:
            local_args.append('--sync={0}'.format(sync))

        if kwargs.get('expand_multi', False):
            local_args.append('--expand-multi')

        field = kwargs.get('field', 'username')
        if field in self.NAMED_FIELDS:
            local_args.append('--{0}'.format(field))
        else:
            local_args.append('--field={0}'.format(field))

        if kwargs.get('basic_regexp', False):
            local_args.append('--basic-regexp')
        elif kwargs.get('fixed_string', False):
            local_args.append('--fixed-strings')

        local_args.append(target)

        return self.run_command('show', local_args)


class LookupModule(LookupBase):

    def run(self, terms, variables=None, **kwargs):
        lp = LastPass(command=kwargs.pop('lastpass_command', None))

        returncode, stdout, stderr = lp.status()
        if returncode != 0:
            raise AnsibleError('lastpass status error: {0}'.format(stdout.rstrip()))

        ret = []
        for term in terms:
            returncode, stdout, stderr = lp.show(term, **kwargs)
            if returncode != 0:
                raise AnsibleError('lastpass error retrieving data for {0}: {1}'.format(term, stderr.rstrip()))

            ret.append(stdout.rstrip())

        return ret
