# sympl-email-changes - changes to Sympl bullseye (and later) email installation

This repository contains the changes I make to the ```exim4``` and ```dovecot``` installations on Sympl for Bullseye and later. The original intention was to provide a better signature of malicious activity in log files, so the firewall generation system can pick up bad IPs and do something about them. Recently, I've felt that the system is insufficiently defensive, and have added some new tests to assist with rejecting known bad IPs early on in the SMTP conversation. The setup has been running for some years on a Sympl system and helps to pick up attempts at exhaustive password decryption amongst other things. My intention here is to allow you to understand what the changes do, and also to allow you to skip a step, if you don't think that it is necessary for you.

The original release of these files contained all the files from the Sympl distribution, I think that this was a mistake and have cut things back so that it contains only the files needed for installation. This release comes with an installation script [Install.sh](Install.sh) that when run will automatically inject the files into a copy of your Sympl system. The original files remain untouched and reverting back to the base distribution is easy. The script is safe to run more than once on the same installation.

To use the ```Install.sh```, copy the [Autoinstall.default](Autoinstall.default) to Autoinstall.conf. This file is also a shell script, setting values for the installation script to choose the parts of the distribution for installation. Also, for some changes, you need to edit in some tailoring values. Mostly, the distribution adds new files to augment the existing installation, there are a few cases where  files need editing or replacing. ```Autoinstall.conf``` is ignored by ```git``` so will be kept on any subsequent ```git pull``` command.

This release also handles the preservation of the original distribution somewhat differently than the previous version. The release initially copies all the files from the ```sympl.d``` directory into ```sympl-local.d```, and then changes the ```Makefile``` in the ```exim4``` and ```dovecot``` directories to use these new directories as the basis for creating the actual configuration files. Two new makefiles are created: ```Makefile.sympl``` for the distributed system, and ```Makefile.local``` for the edited installation. The ```Makefile``` is then a symbolic link to the chosen installation, so a ```make``` command will create the actual configuration. A Python script, ```makefilecheck``` is used to manage the Makefiles. The script has a ```-h``` option which shows the commands that the script understands and their action.

The new layout makes it easy to switch between configurations, and also allows for the ```sympl.d``` directories to be updated without possible damage to the running installation. The file ```/etc/dovecot/sympl.d/10.main/60.sni``` is automatically updated by a sympl subsystem, and recreated as a symbolic link in ```sympl-local.d/10.main``` so the automatic update still works.

### 2024 changes

After some numbers of years using these changes, there are several things that are less than optimum with the approach of pushing all blocking into the firewall.

* The firewall, quite reasonably, has to build up a history of unwanted behaviour for an IP before it will block it. So the miscreant site has a chance of doing what it wants to do for several iterations, and ```exim4``` has to detect and block any problem.

* Most of the blocks in the standard set of configuration files are placed in the ```RCPT``` access control list. At this time in the SMTP conversation, all the information needed to see if this is a valid piece of inbound mail is present. However, part of that validation can be to check on any user ids and passwords, which happens before the ```RCPT``` command is received. So all of the sites wanting to look up user names and passwords will get confirmation of their failure (hopefully) before trying to send some mail. OK, they will only get a few attempts before the firewall will block them, but that few may be too many.

* My firewall, [nftfw](https://nftfw.uk), detects failed password attempts in the mail logs and will block the IP address, limiting the number of attempts that one IP can use. After a small number of attempts, the IP address is loaded into the firewall and is blocked. The IP will continue to stay blocked while nftfw's blacklist scanner finds output from the kernel signalling that the IP has tried again to access the machine. If the IP doesn't attempt to connect, the IP address is moved from being on the active list, but is retained for quite a long period.

* The firewall database of blocked IPs and their activity history had grown to over 4000 entries, of which around 650 were currently active blocked sites. Some of these IPs had been active for over a year. The daily activity of blocking IPs has increased dramatically since I last seriously looked at what was going on. There seem to be many robot sites pointing at my server. They relentlessly and fruitlessly keep trying to connect and were firewall blocked. Looking up these IPs showed that they were very nearly all known to one DNS blacklist or another. Basically what I was doing was slowly mirroring the DNSBL contents in my firewall.

The solution seemed to be to move or replicate some of the checks currently in the ```RCPT``` ACL to earlier in the process.  The only viable candidate for the early checks is in the ```CONNECT``` ACL, because the ACLs that are invoked between the start of the conversation and the ```RCPT``` either don't allow active blocking is one of these, or are just don't run early enough.

So the 2024 changes only need the IP of the connecting machine and:

* Moves the test that uses a reverse lookup of the incoming IP and denies access if there is no associated name. This is a huge win, it's still the case that many bad connections are coming in from machines where there is no reverse PTR record available.

* Sets up DNSBL tests for Spamhaus, Spamcop and Barracuda and deny access on any hit. These work for every connection to the mail system and don't seek permission from the existence of a Sympl control file placed in a server's config area. At this point in the conversation, the destination of the mail is unknown, so this selection cannot be made. The tests that are run can be selected from an Exim4 list.

The result of the changes are spectacular.  I cleaned out the firewall database to reset things, and no unwanted authentication lookups are now happening.  I have blocked via the firewall a couple of IP's that are trying to connect relentlessly, for example several attempts every minute.

### How to install the release

Please note that this release is specifically for the Sympl system running on Bullseye and later.

Download the files into a suitable directory. The easiest way to do this is:

``` sh
git clone https://github.com/pcollinson/sympl-email-changes
```
which will create a directory ```symple-email-changes```. Change into the directory and
copy ```Autoinstall.default``` to ```Autoinstall.conf```. Edit the new file to reflect the changes you want to use, the changes are all numbers and refer to section ids (e.g. ch5) in this document. Then run

``` sh
sudo sh Install.sh
```

After you have done, you need to go to ```/etc/exim4``` and ```/etc/dovecot``` and run

``` sh
sudo make
```

## Dovecot - ch1 - Add authentication logging

I want Dovecot to tell me when failed attempts try to verify identities. Dovecot will do this, but it's not available in the installation. The configuration setting:

``` sh
# Log unsuccessful authentication attempts and the reasons why they failed.
auth_verbose = yes
```
is needed. I've raided the standard distribution to place all the authorisation variables into one file because they are useful to have, and installed the file in:


- [dovecot/sympl.d/10-main/35-log-debug](./dovecot/sympl.d/10-main/35-log-debug)


## Dovecot - ch2 - Add private ports for imap

My machine is not public, in the sense that there are a small number of users who are easily told how to access the services. It's good to move the standard imap ports to somewhere else helping to defeat robot hack attempts from script-kiddies. I remove pop access using the firewall, but you can add a similar setup for pop if you need it. If you are using ```roundcube``` then the standard ports need to be available, but only need to be active for ```localhost```. The control file is missing from the standard Sympl distribution and I include it here. To set it up, you need to edit the port numbers in Autoinstall.conf variables:

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

The next few changes put some work into the  access control list for connections to ```exim4```, so we will be turning away some IP addresses before they've said anything, and all we know about them is their IP address. We want to try to stop IPs that we know are bad from being able to verify users and exhaustively decrypt passwords. However, the checks that follow do stop a lot of bad guys from getting near the mail system.

We want to be able to overcome any checks that are in connect ACL, because all we know is an IP address. It's handy to have a whitelist specifically aimed at bypassing the new connection checking that's being added. This change uses a file in ```/etc/exim4``` called ```whitelist_connect_hosts```. If needed it contains a list of IP addresses that should not be blocked in the connect ACL but can be checked later.

There's a new definition file in the 00-main that accesses the new IP white list file needed to make this check. The file is also is a useful place to put some defines that I'll come to later.

The new file is:

- [exim4/sympl.d/00-main/21-connect-check](./exim4/sympl.d/00-main/21-connect-check)

To invoke the new list, there's a new file in the connect ACL and contains a rule that checks the new whitelist file (if it's there) and accepts connections, avoiding any connect checks. The rule also allows connections from IPs in ```/etc/exim4/whitelist/hosts_by_ip``` file, hosts that we are relaying from (in ```/etc/exim4/relay_from_hosts``` and 'private addresses' - the common public set of local IP addresses.

- [exim4/sympl.d/10-acl/10-acl-check-connect/20-accept-known](./exim4/sympl.d/10-acl/10-acl-check-connect/20-accept-known)


## Exim - ch6 - Use the Sympl/Symbiosis/Nftfw firewall database to block IPs

One of the things lacking in the Symbiosis firewall (used by Sympl) is the lack of feedback into the firewall about sites coming back and trying again. In my experience, sites come back again and again, often over long periods, and I want to block them. The firewalls will remove inactive IPs from active blocking after some number of days, but will keep the IP address for a longer period. This new file looks up the IP in the sqlite3 database managed by the firewall, and blocks known bad IPs whose transgression count is over some threshold with:

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

Exim can ratelimit connections, and generally the only sites that 'legally' send mail very quickly at your machine are known relays, and we've carefully excluded them from these checks. The others are usually spammers or exhaustive decrypters that connect at full bore. The ratelimit provided by this rule doesn't block transgressors, so legal email sites will pick up and start again. It's not that draconian - 10 messages every 15 minutes. It's worth doing, because it generally gives the firewall scanning code time to evaluate the nastiness of the connection, so often when the nasties return they are blocked. The file also logs rates for all-comers, if you don't want this you can comment it out, see the control file.

The new file is:

- [exim4/sympl.d/10-acl/10-acl-check-connect/50-ratelimit](./exim4/sympl.d/10-acl/10-acl-check-connect/50-ratelimit)


## Exim - ch8 - Adding Extra Blacklists

The distributed system checks IPs against Spamhaus blacklists, and I wanted to add others, specifically Barracuda and Spamcop. The rule works the same way as the Spamhaus one, you need to put two files named for their DNS name in ```srv/DOMAIN/config/blacklists``` to include them:

``` sh
b.barracudacentral.org
bl.spamcop.org
```
so they are optional. Spamcop doesn't seem to support IPv6 addresses so these are excluded from that lookup.

The new file is in the check_rcpt ACL:

- [exim4/sympl.d/10-acl/50-acl-check-rcpt/76-dns-blacklists](./exim4/sympl.d/10-acl/50-acl-check-rcpt/76-dns-blacklists)


## Exim - ch9 - Reject connections if there is no reverse PTR record for the IP

This is 'standard' for ```sendmail``` sites, and is a good way of rejecting spammers who often don't have a registered PTR record for their IP. It's wise to run a local caching nameserver to use this, but this is a good idea anyway.

The new file is:

- [exim4/sympl.d/10-acl/50-acl-check-rcpt/77-check-sender-host-name](./exim4/sympl.d/10-acl/50-acl-check-rcpt/77-check-sender-host-name)

## Exim - ch10 - Use Spamhaus Data Query Service for DNSBL lookups

Spamhaus provide a better service if you sign up for an account. You will get a set of private lookup addresses for the account incorporating a personalised key, the addresses replaces the public lookups installed in the Sympl ```exim4``` ACL file. Spamhaus have rules for commercial use and if you qualify they expect you to pay. Incidentally, they do monitor usage and can withhold service if your site transgresses. The fee is not huge and is worth paying when you consider how useful their efforts are. They also provide free 'trial' accounts, see [their website](https://www.spamhaustech.com/free-trial/sign-up-for-a-free-data-query-service-account/), the page also explains the commercial rules. I recommend that you sign up. Since I stopped being commercial, my ID number is still in use, and it's free.

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
to the value of your key. If there is no key, ```exim4``` will ignore the rules needing a Spamhaus key installed in ```75-dns-blacklists```.

## Exim - ch11 - Stop annoying 'no IP address found for host no_matching_hosts' error message

The SMTP protocol has a option ```AUTH``` that tells the incoming client that authorisation is needed. Exim will suppress the command for TCP connections from the local machine, and also for remote connections that have not connected using encryption. While doing this, it creates a list containing the domain name of the incoming machine. Later on, this list is expanded to an IP address. By default, the standard distribution uses ```no_matching_hosts``` as this name when the incoming connection is not using encryption, and the converson of this string to an IP address always fails, giving rise to the error message.


This change replaces ```no_matching_hosts``` by ```localhost```, so the lookup succeeds, but doesn't match the incoming IP address, so the caller is not given the ```AUTH``` option.

The change is made by editing of the control file.

The change is no longer needed in recent versions of Sympl, the change has been adopted into its code. It's now set to not be included by default in the configuration file.

## Exim - ch12 - Reject connections in the Connect ACL if there is no reverse PTR record for the IP (added 2024)

This is a direct copy of the contents of ch9, and drops connections if the IP address doesn't have a partner PTR record with a hostname. If you use this, you can disable the ch9 change. However, doing it twice is relatively free because ```exim4``` caches DNS lookups.

Blocking access in this way is 'standard' for ```sendmail``` sites, and is a good way of rejecting spammers who often don't have a registered PTR record for their IP. It's wise to run a local caching nameserver to use this, but this is a good idea anyway.

As I write, this rule is blocking 30% of sites being blocked in the Connect ACL.

The new file is

- [exim4/sympl.d/10-acl/10-acl-check-connect/21-check-sender-host-name](./exim4/sympl.d/10-acl/10-acl-check-connect/21-check-sender-host-name)

## Exim - ch13 - Test IP addresses in the Connect ACL and reject if found (added 2024)

This change adds three tests on the incoming IP address using Spamhaus, Spamcop and Barracuda. The connection is rejected if the IP address is found in the DNSBL. If you have a Spamhaus ID code and want to use it, ch10 must be enabled. Control files in the ```srv/example.domain/config/blacklists``` are not used to enable the tests. At the connect time in the SMTP conversation the information needed to select ```example.domain``` is not known. Instead a variable defined in ```00-main/22-dns-check-in-connect``` is used to select the tests that are done:

``` sh
DNSBL_CHECK_IN_CONNECT = spamhaus : spamcop : barracuda

```
This variable is an ```exim4``` list, and tests can be suppressed by removing one or more of the entries. The variable does not set the order of tests which are hard coded. This variable is also defined in the ```Autoinstall.conf```.

The tests can skipped for nominated IPs by the whitelisting measures installed in ch5.

Of course, if a connection proceeds to the ```RCPT``` ACL, the DNSBL tests will be done again. However, these should be relatively free because the DNS lookups are cached by ```exim4``` and also by the local DNS server.

The new files are:

- [exim4/sympl.d/00-main/22-dns-check-in-connect](./exim4/sympl.d/00-main/22-dns-check-in-connect)
- [exim4/sympl.d/10-acl/10-acl-check-connect/25-dnsbl-reject](./exim4/sympl.d/10-acl/10-acl-check-connect/25-dnsbl-reject)

## Exim - ch14 - If sender is a known local domain, skip further checking

This change checks the sender domain of the mail against the list of local domains that ```exim4``` knows about. If there is a match, mail processing  will continue, skipping blacklist testing, DNSBL testing, spam and virus scanning.

You might not want to enable this if you want to spam and virus check outbound mail on your server.

I added this to my server in 2022, but it hasn't been integrated in this package until now.

## Finally

These changes are well tried and tested over a couple of years on a Symbiosis system and at the time of writing with several years on a Sympl system. The rules will make your email system more robust and considerably more defensive, containing new features that try harder to keep the bad guys away from your mail system.
