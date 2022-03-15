#!/usr/bin/env python3
""" Main program for filecheck """

import os
import sys
import argparse
from status import AppStatus
from editing import FileEdit

def am_i_root() -> None:
    """Check if running as root and die if not"""

    if os.geteuid() != 0:
        print("Run the program as root")
        sys.exit(1)

def process(args: argparse.Namespace)->None:
    """ Process the arguments """

    # safety
    if args.command == 'uninstall' and \
       not args.force:
        print('The -f argument is needed with the uninstall option')
        sys.exit(1)

    # change default apps
    apps = ['exim4', 'dovecot']
    if args.app != '':
        apps = args.app
    for app in apps:
        appstat = AppStatus(app, args.quiet)
        primary_profile =  appstat.get_overall_status()

        if args.command == 'status':
            appstat.show_info(primary_profile)
            continue

        if args.command == 'report':
            appstat.show_report(primary_profile)
            continue

        makechange = FileEdit(appstat, primary_profile)
        makechange.callfn(args.command)


if __name__ == '__main__':

    DESCR = """Check and fix Makefiles for sympl-email-changes"""
    EPILOG = """
    Commands are:
    status - print status - default when no arguments are given
    report - Return coded action list (used by Install.sh)
    repair - Repair current installation
    sympl  - Set Makefile to link to Makefile.sympl, using sympl.d,
             using installed sympl settings
    local  - Set Makefile link to Makefile.local,
             using sympl-local.d for sympl-email-changes to be active
    revert - Reinstate Makefile as a file, remove Makefile.local & Makefile.sympl
             Remove the sympl-local.d directory by hand.
    """

    am_i_root()

    # check on system version
    try:
        assert sys.version_info >= (3, 9), "Sorry, this script needs Python 3.9 or later."
    except AssertionError as err:
        print(err)
        sys.exit(1)

    ap = argparse.ArgumentParser(
        prog='filecheck',
        description=DESCR,
        epilog=EPILOG,
        formatter_class=argparse.RawTextHelpFormatter)

    ap.add_argument(
        '-q', '--quiet',
        help="Don't print any status information",
        action="store_true")
    ap.add_argument(
        '-a', '--app',
        help="""Selects the app to apply the command to,
        if absent applies to both""",
        choices=('exim4', 'dovecot'),
        nargs=1, default="")
    ap.add_argument(
        '-f', '--force',
        help="Needed when 'uninstall' is used",
        action="store_true")
    ap.add_argument(
        'command',
        nargs='?',
        default="status",
        choices=('status', 'report', 'repair',
                 'sympl', 'local', 'revert'))

    progargs = ap.parse_args()
    process(progargs)
