# sympl-email-changes - changes to Sympl buster email installation

This repository contains the changes I make to the ```exim4``` and ```dovecot``` installations on Sympl for Buster. My intention is to provide a better signature of malicious activity in log files, so the firewall generation system can pick up bad IPs and do something about them. The setup has been running for some years on a Symbiosis system and helps to pick up attempts at exhaustive password decryption amongst other things. My intention here is to allow you to understand what the changes do, and also to allow you to skip a step, if you don't think that it is necessary for you.

The original release of these files contained all the files from the Sympl distribution, I think that this was a mistake and have cut things back so that it contains only the files needed for installation. This release comes with an installation script [Install.sh](Install.sh) that when run will automatically inject the files into your Sympl system having backed up your original files.

To use the ```Install.sh```, copy the [Autoinstall.default](Autoinstall.default) to Autoinstall.conf. This file is also a shell script, setting values for the installation script to choose the parts of the distribution for installation. Also, for some changes, you need to edit in some tailoring values. Mostly the distribution adds new files to augment the installations, there are a few cases where  files need editing or replacing. ```Autoinstall.conf``` is ignored by ```git``` so will be kept on any subsequent ```git pull``` command.

Changes all affect files in the ```sympl.d``` directory in ```/etc/dovecot``` or ```/etc/exim4```. Run the install script, then run move to the relevant directory and use```make``` to install the alterations.

## Pre-install backups

The Install.sh script will make backups of your hopefully vanilla ```/etc/dovecot/sympl.d``` and ```/etc/exim4/sympl.d``` so you can backtrack. When run, the script creates a gzipped tar file in both directories called ```sympl.d.backup.tar.gz``` if the tar file doesn't exist. To recover the original setup, change into the directory and run:

``` sh
$ sudo tar xfz sympl.d.backup.tar.gz
```

which will create a new directory called ```sympl.d.backup```.  If you just need to check what was there before, you can now look. If you want to go back, remove the ```sympl.d``` directory, and rename the backup to ```sympl.d``` in place. Use ```make``` to re-install.

## Dovecot - ch1 - Add authentication logging

I want Dovecot to tell me when failed attempts try to verify identities. Dovecot will do this, but it's not available in the installation. The configuration setting:

``` sh
# Log unsuccessful authentication attempts and the reasons why they failed.
auth_verbose = yes
```
is needed. I've raided the standard distribution to place all the authorisation variables into one file because they are useful to have, and installed the file in:


- [dovecot/sympl.d/10-main/35-log-debug](./dovecot/sympl.d/10-main/35-log-debug)


## Dovecot - ch2 - Add private ports for imap

My machine is not public, in the sense that there are a small number of users who are easily told how to access the services. It's good to move the standard imap ports to somewhere else helping to defeat robot hack attempts from script-kiddies. I remove pop access from the firewall, but you can add a similar setup for pop if you need it. If you are using ```roundcube``` then the standard ports need to be available, but only need to be active for ```localhost```. The control file is missing from the standard Sympl distribution and I include it here. To set it up, you need to edit the port numbers in Autoinstall.conf variables:

``` sh
AUTO_IMAP_PORT=
AUTO_IMAPS_PORT=
```
if you don't, then the option 2 is not installed.

The new file is:

- [dovecot/sympl.d/10-main/15-imap-ports](./dovecot/sympl.d/10-main/15-imap-ports)

## Exim - ch3 - Add +smtp_protocol_error to logging

We want exim to log protocol errors, because this is another way to detect bad things happening. Overall ```exim4``` logging is controlled by a global setting ```log_selector``` and this can only appear once in the configuration files. Unfortunately, it's set in a distributed file ```00-main/50-tls-options```, so this change comments that out and moves control of the flag to a separate file.

The new file is:

- [exim4/sympl.d/00-main/25-logging](./exim4/sympl.d/00-main/25-logging)

The file that needs replacing is:

- [exim4/sympl.d/00-main/50-tls-options](./exim4/sympl.d/00-main/50-tls-options)

This is not installed by Install.sh, instead the script comments out the line in situ.

## Exim - ch4 - replace 'ident' suppression by approved recipe

While we are changing distributed files, it seems sensible to replace the settings that needed to stop the 'ident' operation by a recipe that's supplied by the ```exim4``` documentation. This means commenting out two lines:

``` sh
rfc1413_hosts =
rfc1413_query_timeout = 5s
```

in ```00-main/60-general-options``` and adding a new file that includes the approved setting ```00-main/65-no-ident```.

The new file is:

- [exim4/sympl.d/00-main/65-no-ident](./exim4/sympl.d/00-main/65-no-ident)

The file that needs replacing is:

- [exim4/sympl.d/00-main/60-general-options](./exim4/sympl.d/00-main/60-general-options)

Again, the file is not directly installed by Install.sh, instead the script comments out the two lines in situ.

## Exim - ch5 - Allow skipping of connect ip checking

The next few changes put some work into the  access control list for connections to ```exim4```, so we will be turning away some IP addresses before they've said anything, and all we know about them is their IP address. We want to try to stop IPs that we know are bad from being able to verify users and exhaustively decrypt passwords. At one point I put checks for the IP in the various Blackhole lists in here, but that proved to be overkill, I was just slowly collecting copies of the blacklist  databases. However, the checks that follow do stop a lot of bad guys from getting near the mail system.

We want to be able to overcome any checks that are in connect ACL, because all we know is an IP address. It's handy to have a whitelist specifically aimed at bypassing the new connection checking that's being added. This change uses a file in ```/etc/exim4``` called ```whitelist_connect_hosts```. If needed it contains a list of IP addresses that should not be blocked in the connect ACL but can be checked later.

There's a new definition file in the 00-main that accesses the new IP white list file needed to make this check. The file is also is a useful place to put some defines that I'll come to later.

The new file is:

- [exim4/sympl.d/00-main/21-connect-check](./exim4/sympl.d/00-main/21-connect-check)

To invoke the new list, there's a new file in the connect ACL and contains a rule that checks the new whitelist file (if it's there) and accepts connections, avoiding any connect checks. The rule also allows connections from IPs in ```/etc/exim4/whitelist/hosts_by_ip``` file, hosts that we are relaying from (in ```/etc/exim4/relay_from_hosts``` and 'private addresses' - the common public set of local IP addresses.

- [exim4/sympl.d/10-acl/10-acl-check-connect/20-accept-known](./exim4/sympl.d/10-acl/10-acl-check-connect/20-accept-known)


## Exim - ch6 - Use the Sympl/Symbiosis/Nftfw firewall database to block IPs

One of the things lacking in the Symbiosis firewall (used by Sympl 9) is the lack of feedback into the firewall about sites coming back and trying again. In my experience, sites come back again and again, often over long periods, and we want to block them. The firewalls will remove inactive IPs from active blocking after some number of days, but will keep the IP address for a longer period. This new file looks up the IP in the sqlite3 database managed by the firewall, and blocks known bad IPs whose transgression count is over some threshold with:

``` sh
Blacklisted: Denied access - history of unwanted activity
```

Because this message appears in the mail logs, it can be detected and the firewall state updated, so a returning site that's timed out for inactivity from the firewall will make a re-appearance.

Defines in ```exim4/sympl.d/00-main/21-connect-check``` control the rule, we need to select for different firewalls and system versions.

``` sh
SYMPL_INCIDENT_THRESHOLD = 10
```
will, if defined, include this rule and is used for threshold checking.  We also need where the database is stored.

``` sh
SYMPL_DB = /var/lib/sympl/firewall-blacklist-count.db
```
The database needs a different name for a Symbiosis system.

The new file is:

- [exim4/sympl.d/10-acl/10-acl-check-connect/30-check-sympl-db](./exim4/sympl.d/10-acl/10-acl-check-connect/30-check-sympl-db)

A similar rule exists for the Nftfw firewall, it's also controlled by defines in ```exim4/sympl.d/00-main/21-connect-check```,

``` sh
NFTFW_INCIDENT_THRESHOLD = 10
```
and again, if defined, will include the rule.

The new file for nftfw is:

- [exim4/sympl.d/10-acl/10-acl-check-connect/30-check-nftfw-db](./exim4/sympl.d/10-acl/10-acl-check-connect/30-check-nftfw-db)

The Install.sh script installs all the files and will then append the necessary definitions to ```exim4/sympl.d/00-main/21-connect-check``` depending on the value of

``` sh
AUTO_CH6_DATABASE=
```
which can be set to ```nftfw``` or ```sympl```.  If it's empty, the script will look for installation files and attempt to work out what system is available on the machine.

## Exim - ch7 - Ratelimiting connections

Exim can ratelimit connections, and generally the only sites that 'legally' send mail very quickly at your machine are known relays, and we've carefully excluded them from these checks. The others are usually spammers or exhaustive decrypters that connect at full bore. The ratelimit provided by this rule doesn't block transgressors, so legal email sites will pick up and start again. It's not that draconian - 10 messages every 15 minutes. It's worth doing, because it generally gives the firewall scanning code time to evaluate the nastiness of the connection, so often when the nasties return they are blocked.

The new file is:

- [exim4/sympl.d/10-acl/10-acl-check-connect/50-ratelimit](./exim4/sympl.d/10-acl/10-acl-check-connect/50-ratelimit)


## Exim - ch8 - Adding Extra Blacklists

The distributed system checks IPs against Spamhaus blacklists, and I wanted to add others, specifically Barracuda and Spamcop. The rule works the same way as the Spamhaus one, you need to put two files named for their DNS name in ```srv/DOMAIN/config/blacklists``` to include them:

``` sh
b.barracudacentral.org
bl.spamcop.org
```
so they are optional. Spamcop doesn't seem to support IPv6 addresses so these are excluded from that lookup.

Theo new file is in the check_rcpt ACL:

- [exim4/sympl.d/10-acl/50-acl-check-rcpt/76-dns-blacklists](./exim4/sympl.d/10-acl/50-acl-check-rcpt/76-dns-blacklists)


## Exim - ch9 - Reject connections if there is no reverse PTR record for the IP

This is 'standard' for ```sendmail``` sites, and is a good way of rejecting spammers who often don't have a registered PTR record for their IP. It's probably wise to run a local caching nameserver to use this, but this seems wise to me anyway.

The new file is:

- [exim4/sympl.d/10-acl/50-acl-check-rcpt/77-check-sender-host-name](./exim4/sympl.d/10-acl/50-acl-check-rcpt/77-check-sender-host-name)

## Exim - ch10 - Use Spamhaus Data Query Service for DNSBL lookups

Spamhaus provide a better service if you sign up for an account. You will get a set of private lookup addresses for the account incorporating a personalised key, the addresses replaces the public lookups installed in the Sympl ```exim4``` ACL file. Spamhaus have rules for commercial use and if you qualify they expect you to pay. Incidentally, they do monitor usage and can withhold service if your site transgresses. The fee is not huge and is worth paying when you consider how useful their efforts are. They also provide free 'trial' accounts, see [their website](https://www.spamhaustech.com/free-trial/sign-up-for-a-free-data-query-service-account/), the page also explains the commercial rules. I recommend that you sign up.

This change provides two files enabling the use of these lookup addresses. ```35-spamhaus-key``` defines a macro for the key which is then used in the replacement file ```75-dns-blacklists``` to include the Spamhaus lookup rules. The new rules are added at the top of this file and are only seen by ```exim4``` when the key is defined. The rules are a clone of the original Spamhaus set with the changes made to use the new addresses. The key is suppressed in any log and message sent when a rule is triggered.

The existing rules are activated by placing a file like ```zen.spamhaus.org```  in the appropriate ```srv/example.domain/config/blacklists``` directory. The new rules are actioned with a name like ```zen.dq.spamhaus.net``` so both sets can be used, which I did until I was sure that my key worked.

Both rulesets have been augmented by  tests using the Spamhaus DBL list which looks for known bad sender domains. The tests are activated by using the name ```dbl.spamhaus.org``` or ```dbl.dq.spamhaus.net``` in the ```blacklists``` directory.

The replacement file is:

- [exim4/sympl.d/10-acl/50-acl-check-rcpt/75-dns-blacklists](./exim4/sympl.d/10-acl/50-acl-check-rcpt/75-dns-blacklists)

adding a bunch of new rules to cope with the Spamhaus Key and supporting DBL lookup.

The new control file is:

- [exim4/sympl.d/00-main/35-spamhaus-key](./exim4/sympl.d/00-main/35-spamhaus-key)

the file is installed with no key defined, but the key can be added automatically by editing Autoinstall.conf setting

``` sh
AUTO_SPAMHAUS_DB_KEY=
```
to the value of your key. If there is no key, ```Exim4``` will ignore the rules needing a Spamhaus key installed in ```75-dns-blacklists```.

## Finally

These changes are well tried and tested over some couple of years on a Symbiosis system and at the time of writing with three months on a Sympl system. The rules will make your email system more robust, containing new features and providing information to your firewall to detect and block spammers.
