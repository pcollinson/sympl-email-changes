#!/bin/sh
#
# To use Install.sh,
# copy Autoinstall.default file to Autoinstall.conf where it will be loaded
# when you run Install.sh.
#
# Autoinstall.conf is ignored by git, so will not impact on any future
# pull requests.
#
# There is a a new safety strategy.
# New versions of dovecot/sympl.d and exim4/sympl.d are created in sympl-local.d
# and this is used to compile the configuration
# A python3 program is used to manage the makefiles, and can also be used to
# revert to the original installation
# Type
# sudo ./makefilecheck to run this
# the using -h prints some help information

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
CURRENT_AUTO_VERSION=2
# we need to be on Bullseye
release=$(lsb_release -a 2> /dev/null | awk '/Release/ { print($2) }')
if [ "$release" -lt 11 ]; then
   echo "This command is intended to run only on the Debian Bullseye"
   exit 0
fi
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
# Logging and errors
log() {
    echo "$@"
}
error() {
    echo '****' "$@"
}

# clone a directory name.d to name-local.d
# args are full paths of source and dest
clonedir() {

    SRC=$1
    DST=$2
    CURRENT=$PWD
    if [ ! -d $DST ]; then
	mkdir $DST
	chown --reference $SRC $DST
    fi
    # now this is a little tricky
    # we need to get into the src directory
    # create a tar this seems to be the best way
    # not sure what you cannot use a subshell for the
    # first branch
    sh -c "cd $SRC; tar cf - ." | (cd $DST; tar xfp -)
    cd $CURRENT
}
# replace files in a sympl-local.d directory with
# a symlink to the sympl.d directory
set_symlink() {
    # $1 is the path in etc to the base
    # $2 is the path relative to that
    # $3 is the file
    APP=$1
    DIR=$2
    FILE=$3

    LOCALFILE=${APP}/sympl-local.d/${DIR}/${FILE}
    SYMPLFILE=${APP}/sympl.d/${DIR}/${FILE}
    if [ ! -L "$LOCALFILE" ]; then
	rm -f $LOCALFILE
	ln -s $SYMPLFILE $LOCALFILE
    fi
}

modifyMakefiles() {
    sh makefilefilecheck local
    log "Running make to rebuild the configurations in /etc/dovecot or "
    log "/etc/exim4 will now use new amended sympl-local.d files."
    log "This allows system updates to change log files in "
    log "/etc/dovecot/sympl.d or /etc/exim4/sympl.d without impacting"
    log "changes made here. However system update may change the Makefiles too."
    log "Run the script: sudo makefilecheck to check and set the state of"
    log "the Makefiles. The -j option provides some information on the arguments"
    log "to the scripts."
}

if [ ! -d /etc/dovecot/sympl.d ]; then
   error Cannot find /etc/dovecot/sympl.d
   exit
fi
if [ ! -d /etc/exim4/sympl.d ]; then
   error Cannot find /etc/exim4/sympl.d
   exit
fi

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
# clone files into the new local directories
if [ ! -d /etc/dovecot/sympl-local.d ]; then
    clonedir /etc/dovecot/sympl.d /etc/dovecot/sympl-local.d
fi
if [ ! -d /etc/exim4/sympl-local.d ]; then
    clonedir /etc/exim4/sympl.d /etc/exim4/sympl-local.d
fi
# sympl writes information into
# /etc/dovecot/sympl.d/10-main/60-sni
set_symlink /etc/dovecot 10-main 60-sni

# Destinations
DOVECOT=/etc/dovecot/sympl-local.d
EXIM=/etc/exim4/sympl-local.d
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
	# Check on nftfw
	# look for config files AND the firewall.db
	# because the firewall.db may not be created yet
	NFTFW_DB=""
	if [ "$AUTO_CH6_DATABASE" = "" ]; then
	    rootd=/
	    vard=/usr/local/
	    nconf=etc/nftfw/config.ini
	    nwall=var/lib/nftfw/firewall.db
	    if [ -f $rootd$nconf -o -f $rootd$nwall} ]; then
		AUTO_CH6_DATABASE=nftfw
		NFTFW_DB=$rootd$nwall
	    elif [ -f $vard$nconf -o -f $vard$nwall ]; then
		AUTO_CH6_DATABASE=nftfw
		NFTFW_DB=$vard$nwall
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
		    append="# nftfw database check incident threshold
# see 10-acl/10-acl-check-connect/30-check-nftfw-db
NFTFW_INCIDENT_THRESHOLD = 10
# Location of the database
NFTFW_DB = $NFTFW_DB
"
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
if [ "$AUTO_CH11" = 'Y' ]; then
    # Another change to 50-tls-options
    # replace
    # auth_advertise_hosts = localhost : ${if eq{$tls_cipher}{}{no_matching_hosts}{*}}
    # by
    # auth_advertise_hosts = localhost : ${if eq{$tls_cipher}{}{localhost}{*}}    
    srcfile=$EXIM/00-main/50-tls-options
    isunset=$(grep '^auth_advertise_hosts = localhost : ${if eq{$tls_cipher}{}{no_matching_hosts}.*' ${srcfile})
    if [ "$isunset" != '' ]; then
	sed -i -e '/^auth_advertise_hosts = /s/no_matching_hosts/localhost/' ${srcfile}
	if [ "$?" -eq 0 ]; then
	    log "${srcfile} edit completed"
	else
	    error "${srcfile} edit failed"
	fi
    else
	log "Edit to $srcfile not needed"
    fi
fi
log "Installation complete"
log "Running makefilecheck to establish correct settings for the makefiles."
./makefilecheck local
