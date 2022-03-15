""" Class to examine Makefiles and file setup for sympl_email_changes package
"""

import re
from pathlib import Path
import textwrap
from typing import Dict, Union, Any


class AppStatus:
    """ Look in various places to get the current status for the app """

    # profiles used to check for current state
    # and move to the next one
    # Want to change the snippets line in Makefile.local
    # to search for files (f) AND symlinks (f,l)
    profiles: dict[str, dict[str, dict[str, str]]] = {
        'vanilla': {
            'sympl.d': {
                'type': 'dir',
                'state': 'dir'},
            'sympl-local.d': {
                'type': 'dir',
                'state': 'missing'},
            'Makefile': {
                'type': 'file',
                'state': 'file',
                'snippets_dir': 'sympl.d',
                'snippets_type': 'f'},
            'Makefile.local': {
                'type': 'file',
                'state': 'missing'},
            'Makefile.sympl': {
                'type': 'file',
                'state': 'missing'},
        },
        'caninstall': {
            'sympl.d': {
                'type': 'dir',
                'state': 'dir'},
            'sympl-local.d': {
                'type': 'dir',
                'state': 'dir'},
            'Makefile': {
                'type': 'file',
                'state': 'file',
                'snippets_dir': 'sympl.d',
                'snippets_type': 'f'},
            'Makefile.local': {
                'type': 'file',
                'state': 'missing'},
            'Makefile.sympl': {
                'type': 'file',
                'state': 'missing'},
        },
        'sympl': {
            'sympl.d': {
                'type': 'dir',
                'state': 'dir'},
            'sympl-local.d': {
                'type': 'dir',
                'state': 'dir'},
            'Makefile': {
                'type': 'file',
                'state': 'link',
                'link-to': 'Makefile.sympl'},
            'Makefile.local': {
                'type': 'file',
                'state': 'file',
                'snippets_dir': 'sympl-local.d',
                'snippets_type': 'f,l'},
            'Makefile.sympl': {
                'type': 'file',
                'state': 'file',
                'snippets_dir': 'sympl.d',
                'snippets_type': 'f'},
        },
        'local': {
            'sympl.d': {
                'type': 'dir',
                'state': 'dir'},
            'sympl-local.d': {
                'type': 'dir',
                'state': 'dir'},
            'Makefile': {
                'type': 'file',
                'state': 'link',
                'link-to': 'Makefile.local'},
            'Makefile.local': {
                'type': 'file',
                'state': 'file',
                'snippets_dir': 'sympl-local.d',
                'snippets_type': 'f,l'},
            'Makefile.sympl': {
                'type': 'file',
                'state': 'file',
                'snippets_dir': 'sympl.d',
                'snippets_type': 'f'},
        }
    }

    # used when displaying results so
    # can have results that are not profile names
    installation_state = {
        'vanilla':
            'The system is running the standard Sympl installation and '
            'sympl-email-changes have not been installed.',
        'caninstall':
            'The system is running the standard Sympl installation and '
            'sympl-email-changes have been installed. '
            'sympl-email-changes can be made active. Run the Install.sh '
            'script to install the changes to exim4 and dovecot.',
        'sympl':
            'sympl-email-changes are installed and '
            'configured to run using sympl.d configuration files.',
        'local':
            'sympl-email-changes are installed and '
            'configured to run using sympl-local.d configuration files.',
        'unclear':
            'sympl-email-changes are installed but the configuration '
            'is broken in some way, and repair is needed.',
        'fatal':
    	     'sympl-email-changes are installed but the configuration '
             'is broken in some way, but repair cannot be achieved '
             'automatically. Please look at the files and make changes.'
    }

    def __init__(self, app: str, quiet: bool) -> None:
        """ Class to evaluate current system state

        app is appname
        quiet is True - suppress output

        Creates Status dictionary
        key:  Name of file

        path: Path of file
        type: dir | file
        state: missing | file | dir | link
        snippets_dir: if makefile snippet value
        link-to: if link then where it links
        """

        self.app = app
        # Tell printing not to happen
        self.quiet = quiet

        # Holds the information on the various files
        self.status: Dict[str, Dict[str, Any]] = {}

        # results from profile_search
        self.statuslist: dict[str, list[tuple[str, str]]] = {}

        # fatal message - when results from get_overall_status
        # is 'fatal'
        self.fatal_msg_list: list[str] = []

        # start the processing
        self.build_status()

    def build_status(self) -> None:
        """ Create status dictionary by looking at files """

        for name, pdata in self.profiles['vanilla'].items():
            self.status[name] = self.examine_file(name, pdata['type'])
        # get the app directory into the system
        self.status[self.app] = self.examine_file('', 'dir')
        self.check_links()

    def examine_file(self,
                     file: str,
                     filetype: str) -> dict[str, Union[str, Path]]:
        """ Look at one file and return a dict of its status

        sets up 'type' to be the type from the 'vanilla' profile
        and 'state' to be the file state
        """

        new: Dict[str, Any] = {'path': Path(f'/etc/{self.app}/{file}'), 'type': filetype}
        new['state'] = self.get_file_state(new['path'])
        if new['state'] == 'file':
            # then it should have a snippets_dir
            new['snippets_dir'] = self.read_snippets_dir(new['path'])
            new['snippets_type'] = self.read_snippets_type(new['path'])
        if new['state'] == 'link':
            # get link contents
            link_to = self.read_link(new['path'])
            # normalise the link if necessary
            new['link-to'] = link_to
        return new

    def check_links(self) -> None:
        """ When we have all the files, normalise any links """

        for name, vals in self.status.items():
            if vals['state'] == 'link':
                app_path = self.status[self.app]['path']
                if vals['link-to']:
                    if str(vals['link-to'].parent) == '.':
                        link_to =  app_path / vals['link-to']
                        self.status[name]['link-to'] = link_to
                    if vals['link-to'].parent != app_path:
                        self.status[name]['state'] = 'missing'

    def check_for_basic_installation(self) -> list[str]:
        """ Look to see if the basic directories are present """

        # name of app directory
        appdirstr = str(self.status[self.app]['path'])
        # shortcut for status directory
        status = self.status

        if status[self.app]['state'] == 'missing':
            # App is not installed
            return [f'{self.app} is not installed.']
        if status[self.app]['state'] != 'dir':
            # Sanity check
            return [f'{self.app} is not a directory.']
        if status['sympl.d']['state'] == 'missing':
            # Sympl is not installed
            return [f'sympl.d not found in {appdirstr}.']
        if status['sympl.d']['state'] != 'dir':
            # sanity
            return [f'sympl.d in {appdirstr} is not a directory.']

        # check for any installed files that are not files
        badlist = []
        filemap = {'dir': 'directory', 'file': 'file'}
        for file, vals in status.items():
            if vals['state'] == 'unknown':
                shouldbe = filemap[vals['type']]
                failmsg = f'{file} is not {shouldbe}, '\
                           'please check its state.'
                badlist.append(failmsg)

        # check we have at least one Makefile
        vanilla = self.profiles['vanilla']
        makefiles = [name for name, vals in vanilla.items()
                     if vals['type'] == 'file']
        present = [name for name in makefiles
                   if status[name]['state'] not in ('unknown', 'missing')]
        if not present:
            allmakefiles = ", ".join(makefiles)
            failmsg = f'At least one of {allmakefiles} must be ' \
                        'present to allow this script to run, '\
                        'please check your installation.'
            badlist.append(failmsg)

        return badlist

    def profile_search(self) -> None:
        """ Given a broad match with set of profiles
        see what actions are needed to possibly fix the installation

        creates self.statuslist - dict indexed by the profile name
        the value is a list of filename and the action needed:
        	create - file needs making
        	delete - file needs deleting
        	snippet - snippet in Makefile needs repair
        	relink - file link needs to be changed
        These always apply to Makefiles
        """

        # get possible list
        possibles = self.find_profile_match()

        for profile in possibles:
            repairlist: list[tuple[str, str]] = []
            vals: dict[str, Any]

            for file, vals in self.profiles[profile].items():
                if vals['type'] == 'dir':
                    continue

                filestat: dict[str, Any] = self.status[file]
                if vals['state'] != filestat['state']:
                    if filestat['state'] == 'missing':
                        repairlist.append((file, 'Create'))
                    elif vals['state'] == 'missing':
                        repairlist.append((file, 'Delete'))
                else:
                    if vals['state'] == 'file':
                        if 'snippets_dir' not in filestat or \
                                filestat['snippets_dir'] == '' or \
                                vals['snippets_dir'] != filestat['snippets_dir']:
                            repairlist.append((file, 'Repair snippets_dir in'))
                        if 'snippets_type' not in filestat or \
                                filestat['snippets_type'] == '' or \
                                vals['snippets_type'] != filestat['snippets_type']:
                            repairlist.append((file, 'Repair snippets_type in'))
                    if vals['state'] == 'link':
                        if 'link-to' not in filestat or \
                                not filestat['link-to'] or \
                                vals['link-to'] != filestat['link-to'].name:
                            repairlist.append((file, 'Relink'))
                self.statuslist[profile] = repairlist

    def get_overall_status(self) -> str:
        """ Get the system status and return a code and
        some help information. In a separate function to allow
        for the status report and also the report option

        for 'fatal' - returns string description
        for taken from installation state returns a list
        of tuples which ar
        (filename, code) - see profile_search for codes
        """

        installfail = self.check_for_basic_installation()
        if installfail:
            self.fatal_msg_list = installfail
            return 'fatal'

        fatalmsg = ["Sorry it's not been possible to find any profile that " \
                            "fits your system. This should not happen."]
        self.profile_search()

        if len(self.statuslist) == 0:
            self.fatal_msg_list = fatalmsg
            return 'fatal'

        primary_profile = 'fatal'
        keys = self.statuslist.keys()
        if len(keys) == 1:
            # vanilla and caninstall profiles are
            # mutually exclusive and will always occur
            # without sympl or local
            primary_profile = list(keys)[0]
        else:
            # we will have two keys which are sympl and local
            # See if Makefile is a link and points to one of them
            makefile_status = self.status['Makefile']
            primary_profile = 'unclear'
            if makefile_status['state'] == 'link':
                if 'link-to' in makefile_status:
                    if makefile_status['link-to'] == self.status['Makefile.local']['path']:
                        primary_profile = 'local'
                    if makefile_status['link-to'] == self.status['Makefile.sympl']['path']:
                        primary_profile = 'sympl'

        if primary_profile == 'fatal':
            self.fatal_msg_list = fatalmsg
            return 'fatal'
        return primary_profile

    def show_info(self,
                  primary_profile: str,
                  lineone: str = "") -> None:
        """ Display information """

        self.print_title()
        if lineone != "":
            self.print_indent(lineone)

        if primary_profile == 'fatal':
            self.print_indent_list(self.fatal_msg_list)
            return

        self.print_indent(self.installation_state[primary_profile])
        if primary_profile != 'unclear':
            self.display_file_changes(
                "Using 'repair' with this script will:",
                self.statuslist[primary_profile])
            return
        for key, vals in self.statuslist.items():
            if vals:
                self.display_file_changes(
                    f"Running this script with a '{key}' option "
                    "will make these changes",
                    vals)

    def show_report(self, primary_profile: str) -> None:
        """ Return primary_profile code """

        print(f'{self.app}\t{primary_profile}')

    def display_file_changes(self, msg:str, chgs: list[tuple[str, str]]) -> None:
        """ Display any file changes that are needed """

        if chgs:
            self.print_indent(msg)
            for file, cmd in chgs:
                self.print_indent(f'    {cmd} {file}')

    def find_profile_match(self) -> list[str]:
        """ Find possible matching profiles from the data we have

        This looks at the directories first, and then the Makefiles
        The isdisjoint test rejects profiles that just don't match

        returns list of possible profiles
        """

        out: set[str] = set()
        for key, val in self.status.items():
            if key == self.app:
                continue
            reslist = self.profile_scan(key, val['state'])
            if reslist:
                resout = set(reslist)
                if len(out) == 0:
                    out = resout
                else:
                    if not out.isdisjoint(resout):
                        out = resout.intersection(out)
        return list(out)

    def get_file_state(self, file: Any, ispath=True) -> str:
        """ Returns file state

        is ispath is False, then file is a string
        and can be converted using path in self.status

        returns:
        link if a symlink
        missing if the file is not there
        file if it's a file
        dir if it's a directory
        unknown if it's anything else
        """

        if ispath:
            thepath = file
        else:
            thepath = self.status[file]['path']
        if thepath.is_symlink():
            return 'link'
        if not thepath.exists():
            return 'missing'
        if thepath.is_file():
            return 'file'
        if thepath.is_dir():
            return 'dir'
        return 'unknown'

    def read_snippets_dir(self, file: Any, ispath=True) -> str:
        """ Look in a Makefile for the line starting with snippets_dir

        The Makefile is assumed to exist
        return value is the string that is found
        """

        if ispath:
            thepath = file
        else:
            thepath = self.status[file]['path']
        contents = thepath.read_text()
        found = re.search(r'^snippets_dir\s*:=\s*([-a-z0-9.]*).*$',
                          contents,
                          re.MULTILINE)
        if found:
            if found.group(1):
                return found.group(1)
        return ""

    def read_snippets_type(self, file: Any, ispath=True) -> str:
        """ Look in a Makefile for the line starting with snippets
        and extract the value of the -type argument

        The Makefile is assumed to exist
        return value is the string that is found
        """

        if ispath:
            thepath = file
        else:
            thepath = self.status[file]['path']
        contents = thepath.read_text()
        found = re.search(r'^snippets\s*:=\s.*-type\s*([lf,]*)\s.*$',
                          contents,
                          re.MULTILINE)
        if found:
            if found.group(1):
                return found.group(1)
        return ""


    def read_link(self, file: Any, ispath=True) -> Path:
        """ Read the contents of a symlink
        NB needs Python 3.9
        """
        if ispath:
            thepath = file
        else:
            thepath = self.status[file]['path']
        out = thepath.readlink()
        return out

    def profile_scan(self, key: str, val: str) -> list[str]:
        """ Scan profiles looking for a key that matches the value
        return a list of possibles
        """

        result = [name for name, prof in self.profiles.items()
                  if prof[key]['state'] == val]
        return result

    #
    # Text formatting
    #
    def print_title(self) -> None:
        """ Print title name """

        if not self.quiet:
            print(f'{self.app}:')

    @staticmethod
    def wrap(txt: str) -> str:
        """ interface to textwrap.wrap """

        wrapped = textwrap.wrap(txt)
        return "\n".join(wrapped)

    def print_wrap(self, txt: str) -> None:
        """ print wrapped string """

        if not self.quiet:
            print(self.wrap(txt))

    @staticmethod
    def indent(txt: str) -> str:
        """ interface to textwrap.wrap with indent """

        wrapped = textwrap.wrap(txt,
                                subsequent_indent='    ',
                                initial_indent='    ')
        return "\n".join(wrapped)

    def print_indent(self, txt: str) -> None:
        """ print indented string """

        if not self.quiet:
            print(self.indent(txt))

    def indent_list(self, txtlist: list[str]) -> str:
        """ Indent a list """

        out = []
        for txt in txtlist:
            out.append(self.indent(txt))
        return "\n".join(out)

    def print_indent_list(self,
                          txtlist: list[str]) -> None:
        """ print indented string """

        if not self.quiet:
            print(self.indent_list(txtlist))
