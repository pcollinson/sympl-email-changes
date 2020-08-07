#!/bin/sh
#
# To use Install.sh,
# copy Autoinstall.default file to Autoinstall.conf where it will be loaded
# when you run Install.sh.
#
# Autoinstall.conf is ignored by git, so will not impact on any future
# pull requests.
#
if [ "$ZSH_VERSION" != "" ]; then
   emulate -L sh
fi
# Need to be root
iam=$(whoami)
if [ ${iam} != 'root' ]; then
    echo 'This script needs to be run by root'
    exit 1
fi
#
CURRENT_AUTO_VERSION=1
# Check for Autoinstall.conf
if [ ! -f Autoinstall.conf ]; then
    echo "Copy Autoinstall.default to Autoinstall.conf control this script"
    echo "Refer to the README.md file to select which changes you want to"
    echo "install. Some changes need extra information that is supplied"
    echo "by the Autoinstall files."
    exit 1
else
    . ./Autoinstall.conf
    if [ "$AUTO_VERSION" -ne $CURRENT_AUTO_VERSION ]; then
	echo "Automatic nftfw installation problem"
	echo "The version number in Autoinstall.conf does not match the expected"
	echo "value. There's probably been a change in this script needing a new"
	echo "value in Autoinstall.default."

	echo "Please recreate Autoinstall.conf from the current Autoinstall.default,"
	echo "or delete the file to run this script interactively."
	exit 0
    fi
fi
# Looging and errors
log() {
    echo "$@"
}
error() {
    echo '****' "$@"
}
# backup original files in sympl.d
# Create a backup file called sympl.d.backup.tar.gz
# containing the directory contents
# Called with path to directory to work in
backup() {
    # work in a subshell to allow chdir
    (
	cd $1
	log "Backup $1/sympl.d"
	if [ ! -d sympl.d ]; then
	    error "Cannot find $1/sympl.d"
	elif [ -f sympl.d.backup.tar.gz ]; then
	    log "Backup not needed - file exists in $1"
	elif [ -d sympl.d.backup ]; then
	    error "Backup directory sympl.d.backup exists in $1"
	elif [ -h sympl.d.backup ]; then
	    error "Symbolic link sympl.d.backup exists in $1"
	else
	    ln -s sympl.d sympl.d.backup
	    tar cfhz sympl.d.backup.tar.gz sympl.d.backup
	    rm sympl.d.backup
	    log "Created backup of sympl.d in $1/sympl.d.backup.tar.gz"
	    log "When unpacked will create a new directory sympl.d.backup"
        fi
    )
}

# Create a testing environment
createtest() {
    CURRENT=$(pwd)
    BASE=$1
    mkdir $BASE/etc
    mkdir $BASE/etc/exim4 $BASE/etc/dovecot
    # copy current files
    cd /etc/dovecot
    tar cf - sympl.d | (cd $BASE/etc/dovecot && tar xf -)
    cd /etc/exim4
    tar cf - sympl.d | (cd $BASE/etc/exim4 && tar xf -)
    cd $CURRENT
}

if [ "$AUTO_TEST" = 'Y' ]; then
    if [ ! -d $AUTO_TEST_BASE/etc ]; then
	if [ "$AUTO_TEST_CREATE" = 'Y' -a -d /etc/dovecot/sympl.d -a -d /etc/exim4/sympl.d ]; then
	    createtest $AUTO_TEST_BASE
	else
	    error "Not a Sympl system, need testing files - please create them"
	    exit
	fi
    fi
    TESTING=$AUTO_TEST_BASE
fi

if [ ! -d $TESTING/etc/dovecot/sympl.d ]; then
   error Cannot find $TESTING/etc/dovecot/sympl.d
   exit
fi
if [ ! -d $TESTING/etc/exim4/sympl.d ]; then
   error Cannot find $TESTING/etc/exim4/sympl.d
   exit
fi

# Backup original sympl.d contents
backup $TESTING/etc/dovecot
backup $TESTING/etc/exim4

# Sources
DOVESRC=dovecot/sympl.d
EXIMSRC=exim4/sympl.d
for src in $DOVESRC $EXIMSRC
do
    if [ ! -d $src ]; then
	echo "Cannot find $src in current directory"
	echo "Run this script from the distribution directory"
	exit 1
    fi
done
# Destinations
DOVECOT=$TESTING/etc/dovecot/sympl.d
EXIM=$TESTING/etc/exim4/sympl.d
for dest in $DOVECOT $EXIM
do
     if [ ! -d $dest ]; then
	 echo "Cannot find $dest - exiting"
	 exit 0
     fi
done
export DOVESRC EXIMSRC DOVECOT EXIM
# Add a new file
# Args are
# srcbase
# destbase
# file
newfile() {
    srcf=$1/$3
    destf=$2/$3

    if [ ! -f $srcf ] ; then
	error $srcf missing from distribution
	return 1
    fi
    log Installing $destf
    cp $srcf $destf
}
# Add new dovecot file or files
# Args are possible list of files
newdovecot() {
    for file in "$@"
    do
	newfile $DOVESRC $DOVECOT $file
    done
}
newexim() {
    for file in "$@"
    do
	newfile $EXIMSRC $EXIM $file
    done
}

# Installation
if [ "$AUTO_CH1" = 'Y' ]; then
    newdovecot 10-main/35-log-debug
fi
if [ "$AUTO_CH2" = 'Y' ]; then
    if [ "$AUTO_IMAP_PORT" = "" -o "$AUTO_IMAPS_PORT" = "" ]; then
	error "Change 2 is selected, but one or both alternative ports are not defined"
	error "Installation skipped"
    else
	file=10-main/15-imap-ports
	srcf=$DOVESRC/$file
	if [ ! -f $srcf ]; then
	    error $srcf missing from distribution
	else
	    tmp=/tmp/sympl-install.$$
	    sed -e "s/YOUR IMAP PORT/$AUTO_IMAP_PORT/" -e "s/YOUR IMAPS PORT/$AUTO_IMAPS_PORT/" $srcf > $tmp
	    destf=$DOVECOT/$file
	    log Installed edited $destf
	    mv $tmp $destf
	fi
    fi
fi
if [ "$AUTO_CH3" = 'Y' ]; then
    newexim 00-main/25-logging
    # rather than replacing 00-main/50-tls-options
    # edit out the log string in case other parts of the
    # file have been updated
    srcfile=$EXIM/00-main/50-tls-options
    # do the sed edit in a function so we can see if it's done
    edit50() {
	sed -i -e '/^log_selector = +tls_sni$/c\
# Moved to 25-logging\
# log_selector = +tls_sni' $1
	return $?
	}
    if [ ! -f $srcfile ]; then
       error "Cannot find $srcfile"
    elif grep '^log_selector = +tls_sni$' $srcfile > /dev/null; then
	 if edit50 $srcfile ; then
	     log "Edited $srcfile"
	 else
	    error "Edit of $srcfile failed"
	    error "Check that the line"
	    error "log_selector = +tls_sni"
	    error "is commented out"
	 fi
    else
	log "Edit to $srcfile not needed"
    fi
fi
if [ "$AUTO_CH4" = 'Y' ]; then
    newexim 00-main/65-no-ident
    # rather than replacing 00-main/60-general-options
    # comment out the two lines in case other parts of the
    # file have been updated
    srcfile=$EXIM/00-main/60-general-options
    # do the sed edit in a function so we can see if it's done
    # or needed to be done
    edit60() {
	sed -i -e '/^rfc1413_hosts/i\
# Two lines commented out - replaced by approved recipe in 65-no-ident' -e '/^rfc1413_hosts/s/^/# /' -e '/^rfc1413_query_timeout/s/^/# /' $1
	return $?
	}
    if [ ! -f $srcfile ]; then
       error "Cannot find $srcfile"
    elif grep '^rfc1413_hosts' $srcfile > /dev/null; then
	if edit60 $srcfile; then
	    log "Edited $srcfile"
	else
	    error "Edit of $srcfile failed"
	    error "Check that the two lines"
	    error "rfc1413_hosts ="
	    error "rfc1413_query_timeout = 5s"
	    error "are commented out."
        fi
    fi
fi
if [ "$AUTO_CH5" = 'Y' ]; then
    newexim 00-main/21-connect-check 10-acl/10-acl-check-connect/20-accept-known
fi
if [ "$AUTO_CH6" = 'Y' ]; then
    newexim 10-acl/10-acl-check-connect/30-check-sympl-db 10-acl/10-acl-check-connect/30-check-nftfw-db
    if [ ! -f $EXIM/00-main/21-connect-check ]; then
	error Cannot find $EXIM/00-main/21-connect-check to add defines
    else
	symbiosisdb=/var/lib/symbiosis/firewall-blacklist-count.db
	sympldb=/var/lib/sympl/firewall-blacklist-count.db
	nftfwlocal=/usr/local/etc/nftfw/config.ini
	nftfwroot=/etc/nftfw/config.ini
	if [ "$AUTO_CH6_DATABASE" = "" ]; then
	    if [ -f $nftfwlocal -o -f $nftfwroot ]; then
		AUTO_CH6_DATABASE=nftfw
	    elif [ -f $sympldb ]; then
		AUTO_CH6_DATABASE=sympl
	    elif [ -f $symbiosisdb ]; then
		AUTO_CH6_DATABASE=symbiosis
	    else
		error "Cannot identify firewall type - please edit AUTO_CH6_DATABASE"
	    fi
	fi
	if [ "$AUTO_CH6_DATABASE" != "" ]; then
	    append=""
	    case "$AUTO_CH6_DATABASE" in
		nftfw)
		    append='# nftfw database check incident threshold
# see 10-acl/10-acl-check-connect/30-check-nftfw-db
NFTFW_INCIDENT_THRESHOLD = 10
'
		    ;;
		sympl)
		    append='# Sympl database check incident threshold
# see 10-acl/10-acl-check-connect/30-check-sympl-db
SYMPL_INCIDENT_THRESHOLD = 10
# For Sympl
SYMPL_DB = /var/lib/sympl/firewall-blacklist-count.db
'
		    ;;
		symbiosis)
		    append='# Symbiosis database check incident threshold
# see 10-acl/10-acl-check-connect/30-check-sympl-db
SYMPL_INCIDENT_THRESHOLD = 10
# For Symbiosis
SYMPL_DB = /var/lib/symbiosis/firewall-blacklist-count.db
'
		    ;;
            esac
	    if [ "$append" != '' ]; then
		echo "$append" >> $EXIM/00-main/21-connect-check
		log "Appended to $EXIM/00-main/21-connect-check:"
		log "$append"
	    fi
	fi
    fi
fi
if [ "$AUTO_CH7" = 'Y' ]; then
    newexim 10-acl/10-acl-check-connect/50-ratelimit
fi
if [ "$AUTO_CH8" = 'Y' ]; then
    newexim 10-acl/50-acl-check-rcpt/76-dns-blacklists
fi
if [ "$AUTO_CH9" = 'Y' ]; then
    newexim 10-acl/50-acl-check-rcpt/77-check-sender-host-name
fi
if [ "$AUTO_CH10" = 'Y' ]; then
    newexim 00-main/35-spamhaus-key 10-acl/50-acl-check-rcpt/75-dns-blacklists
    if [ "$AUTO_SPAMHAUS_DB_KEY" != "" ]; then
       append="SPAMHAUS_DQ_KEY = $AUTO_SPAMHAUS_DB_KEY"
       echo "$append" >> $EXIM/00-main/35-spamhaus-key
       log "Spamhaus key added to $EXIM/00-main/35-spamhaus-key"
    fi
fi
log "Installation complete"
