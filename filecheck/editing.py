""" Class to change files as needed by the user commands """

import os
import re
from pathlib import Path
from status import AppStatus

class FileEdit:
    """ Execute commands selected by the user """

    def __init__(self,
                 app_status: AppStatus,
                 primary_profile: str,
                 ) -> None:
        """ Edit files based on

        app_status is an instance of AppStatus
        primary_profile is the educated guess about the installed
            status
        statuslist is the result of the scan
        """

        self.app_status = app_status
        self.primary_profile = primary_profile

        # objects we would like access to
        # name of app
        self.app = self.app_status.app

        # current file status
        self.status = self.app_status.status
        #
        # get owner of app directory
        app_path = self.status[self.app]['path']
        self.uid, self.gid = self.getowner(app_path)
        #
        # list of actions
        self.actionlog:list[str] = []
        self.reload_needed = False

    @staticmethod
    def getowner(fpath: Path) -> tuple[int, int]:
        """ Get the uid, gid for a filepath """

        statobj = fpath.stat()
        uid = statobj.st_uid
        gid = statobj.st_gid
        return (uid, gid)

    def callfn(self, command: str) -> None:
        """ Execute a function from the command

        but the status returned by assess must allow
        changes to be make
        """

        if self.primary_profile in ['vanilla', 'fatal']:
            self.inappropriate(command)
            return

        action = getattr(self, command)
        action()

    def inappropriate(self, command:str) -> None:
        """ Print a cannot do this message """

        msg = f"The {command} option cannot be applied to {self.app}."
        self.app_status.show_info(self.primary_profile,
                                  lineone = msg)

    def reload_instructions(self, primary_profile: str) -> None:
        """ tell the user what to do next """

        print_title = self.app_status.print_title
        print_indent = self.app_status.print_indent
        print_indent_list = self.app_status.print_indent_list

        instate = self.app_status.installation_state[primary_profile]
        print_title()
        print_indent(instate)
        if self.actionlog:
            print_indent('Actions:')
            print_indent_list(self.actionlog)
        else:
            print_indent('Actions: none')
        if self.reload_needed:
            print_indent(f'Now - to configure {self.app}')
            print_indent(f"    cd /etc/{self.app}")
            print_indent("    sudo make")

    def edit_snippets(self,
                      inname: str,
                      outname: str,
                      dir_setting: str,
                      type_setting: str) -> None:
        """ Copy inname to outname replacing the snippets_dir and snippets lines """

        fpath = self.status[inname]['path']
        contents = fpath.read_text()
        lines = contents.split('\n')
        out = []
        compiledirre = re.compile(r'snippets_dir')
        replacedirline = f'snippets_dir := {dir_setting}'
        compiletypere = re.compile(r'^(snippets\s*:=.*-type\s)[lf,]*(.*)$')
        dir_done = False
        type_done = False
        for line in lines:
            if not dir_done:
                match = compiledirre.match(line)
                if match:
                    out.append(replacedirline)
                    dir_done = True
                    continue
            if not type_done:
                match = compiletypere.match(line)
                if match:
                    left = match.group(1)
                    right = match.group(2)
                    outline = f'{left}{type_setting}{right}'
                    out.append(outline)
                    type_done = True
                    continue
            out.append(line)
        newcontents = "\n".join(out)
        outpath = self.status[outname]['path']
        outpath.write_text(newcontents)
        self.setowner(fpath)

    def setowner(self, fpath:Path) -> None:
        """ Set the owner of a file """

        os.chown(fpath, self.uid, self.gid, follow_symlinks=False)

    def match_profile(self, wanted: str) -> None:
        """ Check wanted profile against what's installed

        Make necessary changes
        """

        profile = self.app_status.profiles[wanted]
        status = self.status

        # May need a working text Makefile
        textfile = ""
        for name, vals in status.items():
            if vals['type'] == 'file' and \
               vals['state'] == 'file' and \
               'snippets_dir' in  vals and \
               vals['snippets_dir'] != "":
                textfile = name
                break

        if textfile == "":
            # Then we cannot find a suitable file
            # to act as a template
            self.actionlog.append('*** Unable to make changes. No Makefile with a valid '
                           "'snippets_dir' entry was found. "
                           'Please look at the files and repair them.'
                           )
            return

        # First check on text Makefiles
        deletelist = []
        for name in ['Makefile.local', 'Makefile.sympl']:
            make_profile = profile[name]
            make_status = status[name]
            if make_profile['state'] == make_status['state'] and \
               ( make_profile['state'] == 'missing' or \
                 ( make_profile['snippets_dir'] == make_status['snippets_dir'] and \
                   make_profile['snippets_type'] == make_status['snippets_type']
                 )
                ):
                # Nothing to do
                continue
            if make_profile['state'] == 'missing':
                deletelist.append(name)
            elif make_status['state'] == 'missing' or \
                 'snippets_dir' not in make_status or \
                 make_profile['snippets_dir'] != make_status['snippets_dir'] or \
                 make_profile['snippets_type'] != make_status['snippets_type']:
                # This will create the file if needed
                self.edit_snippets(textfile,
                                   name,
                                   make_profile['snippets_dir'],
                                   make_profile['snippets_type'])
                # tart up logging
                if make_status['state'] == 'missing':
                    reason = 'created'
                else:
                    reason = 'replaced snippets_dir and snippets_type'
                self.actionlog.append(f'{name} {reason}')

        # Now deal with Makefile
        make_profile = profile['Makefile']
        make_status = status['Makefile']
        if make_profile['state'] == 'link':
            link_path = status[make_profile['link-to']]['path']

            if make_status['state'] in ('file', 'missing') or \
               'link-to' not in make_status or \
               link_path != make_status['link-to']:

                if make_status['state'] != 'missing':
                    make_status['path'].unlink()
                destfile = make_profile['link-to']
                destpath = status[destfile]['path']
                make_status['path'].symlink_to(destpath)
                self.actionlog.append(f'Makefile linked to {destfile}')
                self.reload_needed = True

        else: # will be a file
            if make_status['state'] == 'link' or \
               make_profile['snippets_dir'] != make_status['snippets_dir'] or \
               make_profile['snippets_type'] != make_status['snippets_type']:
                if make_status['state'] == 'link':
                    make_status['path'].unlink()
                self.edit_snippets(textfile,
                                   'Makefile',
                                   make_profile['snippets_dir'],
                                   make_profile['snippets_type'])
                self.actionlog.append('Makefile created')
                self.reload_needed = True

        for deletefile in deletelist:
            status[deletefile]['path'].unlink()
            self.actionlog.append(f'{deletefile} deleted')

    #
    # Actions
    #

    def local(self) -> None:
        """ Set profile to local """

        self.match_profile('local')
        self.reload_instructions('local')

    def sympl(self) -> None:
        """ Set profile to sympl """

        self.match_profile('sympl')
        self.reload_instructions('sympl')

    def repair(self) -> None:
        """ Repair the current installation
        using primary_profile as the key
        """

        primary_profile = self.primary_profile
        if primary_profile in ('unclear',
                               'vanilla'):
            if primary_profile == 'unclear':
                msg = 'There is not enough information for ' \
                      'automatic repair, run this script again ' \
                       "using 'sympl' or 'local' as an argument."
            else:
                msg = 'The sympl_email_changes package is not ' \
                      'installed yet.'
            self.app_status.show_info(self.primary_profile,
                                      lineone = msg)
        else:
            self.match_profile(primary_profile)
            self.reload_instructions(primary_profile)

    def revert(self) -> None:
        """ Revert to caninstall """

        self.match_profile('caninstall')
        self.reload_instructions('caninstall')
