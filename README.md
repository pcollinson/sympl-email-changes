# sympl-email-changes - changes to Sympl buster email installation

This repository contains the changes I make to the ```exim4``` and ```dovecot``` installations on Sympl for Buster. My intention is to provide a better signature of malicious activity in log files, so the firewall generation system can pick up bad IPs and do something about them. The setup has been running for some years on a Symbiosis system and helps to pick up attempts at exhaustive password decryption amongst other things. I'm moving from the distributed files and inserting files from a running installation. My intention is to allow you to understand what the changes do, and also to allow you to skip a step, if you don't think that it is necessary for you.

I am starting from the configuration files supplied with Sympl as of 29/April/2020. The ```dovecot``` and ```exim4``` directories are installed without cloning, because there is no mileage in having the whole sympl installation replicated here. I'm altering the set of files step by step with a git commit at every stage. This file supplies a description of what each change does.

Changes all affect files in the ```sympl.d``` directory in ```/etc/dovecot``` or ```/etc/exim4```. Change the files, then run ```make``` in the relevant directory to install the alterations.

## Dovecot - ch1 - Add authentication logging

I want Dovecot to tell me when failed attempts are made to verify identities. It will do this, but it's not available in the installation. The configuration setting:

``` sh
# Log unsuccessful authentication attempts and the reasons why they failed.
auth_verbose = yes

```
is needed. I've raided the standard distribution to place all the authorisation variables into one file because they are useful to have, and installed the file in:

``` sh
[dovecot/sympl.d/10-main/35-log-debug](dovecot/sympl.d/10-main/35-log-debug)
```

## Dovecot - ch2 - Add private ports for imap

My machine is not public, in the sense that everyone using it is known and so it's good to move the standard imap ports to somewhere else, which helps to defeat the robot attempts from script-kiddies. I remove pop access from the firewall, but a similar setup can be installed. If you are using ```roundcube``` then the standard ports need to be available, but only need to be active for ```localhost```. Again this file is missing from the standard Sympl distribution and I include it to assist you to do this. Look at the file, you'll need to supply your own private port numbers - replace ```YOUR PORT``` by two numbers.

The new file is:

``` sh
[dovecot/sympl.d/10-main/15-imap-ports](dovecot/sympl.d/10-main/15-imap-ports)
```

## Exim - ch3 - Add +smtp_protocol_error to logging

We want exim to log protocol errors, because this is another way to detect bad things happening. Overall ```exim4``` logging is controlled by a global setting ```log_selector``` and this can only appear once in the configuration files. Unfortunately, it's set in a distributed file ```00-main/50-tls-options```, so this change comments that out and moves control of the flag to a separate file.

The new file is:

``` sh
[exim4/sympl.d/00-main/25-logging](exim4/sympl.d/00-main/25-logging)
```

The file that needs replacing is:

``` sh
[exim4/sympl.d/00-main/50-tls-options](exim4/sympl.d/00-main/50-tls-options)
```

## Exim - ch4 - replace 'ident' suppression by approved recipe

While we are changing distributed files, it seems sensible to replace the settings that are intended to stop the 'ident' operation by a recipe that's supplied by the ```exim4`` documentation. This means commenting out two lines:

``` sh
rfc1413_hosts =
rfc1413_query_timeout = 5s
```

in ```00-main/60-general-options``` and adding a new file that includes the approved setting ```00-main/65-no-ident```.

The new file is:

``` sh
[exim4/sympl.d/00-main/65-no-ident](exim4/sympl.d/00-main/65-no-ident)
```

The file that needs replacing is:

``` sh
[exim4/sympl.d/00-main/60-general-options](exim4/sympl.d/00-main/60-general-options)
```

## Exim - ch5 - Allow skipping of connect ip checking

The next few changes put some work into the connect access control list, so we will be turning away some IP addresses before they've said anything, and all we know about them is their IP address. We want to try to stop IPs that we know are bad from being able to verify users and exhaustively decrypt passwords. At one point I put checks for the IP in the various Blackhole lists in here, but that proved to be overkill, I was just slowly collecting their databases. However, the checks that follow do stop a lot of bad guy from getting near the mail system.

We want to be able to overcome any checks that are in connect ACL, because we don't know much about them. We can select based on the 'good' IPs we know, but it's handy to be able to add an IP into the list. So this change uses a file in ```/etc/exim4``` called ```whitelist_connect_hosts```. If needed it contains a list of IP addresses that should not be checked in the connect ACL.

There's a new file in the 00-main that defines the hostlist needed to make this check. It also is a useful place to put some defines that I'll come to later.

The new file is:
``` sh
[exim4/sympl.d/00-main/21-connect-check](exim4/sympl.d/00-main/21-connect-check)
```
and we need a file that checks this file if it's there and accepts connections, avoiding any connect checks. The file also allows connections from IPs in ```/etc/exim4/whitelist/hosts_by_ip``` file, hosts that we are relaying from (in ```/etc/exim4/relay_from_hosts``` and 'private addresses' - the common public set of local IP addresses.

The file is
``` sh
[exim4/sympl.d/10-acl-check-connect/20-accept-known](exim4/sympl.d/10-acl-check-connect/20-accept-known)
```

## Exim - ch6 - Use the Sympl/Symbiosis/Nftfw firewall database to block IPs

One of the things lacking in the Symbiosis firewall (currently run by Sympl) is the lack of feedback into the firewall about sites coming back and trying again. In my experience, sites come back again and again, and we want to block them. This new file looks up the IP in the sqlite3 database managed by the firewall, and blocks newcomers with

``` sh
Blacklisted: Denied access - history of unwanted activity
```

if the count of their transgressions is over some threshold. Because this message appears in the mail logs, it can be detected and the firewall state updated, so a returning site that's timed out will make a re-appearance in the firewall. 

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

``` sh
[exim4/sympl.d/10-acl/10-acl-check-connect/30-check-sympl-db](exim4/sympl.d/10-acl/10-acl-check-connect/30-check-sympl-db)
```

A similar rule exists for the Nftfw firewall, it's also controlled by a define in ```exim4/sympl.d/10-acl/10-acl-check-connect```,

``` sh
NFTFW_INCIDENT_THRESHOLD = 10
```
and again, if defined, will include the rule.

The new file for nftfw is:

``` sh
[exim4/sympl.d/10-acl/10-acl-check-connect/30-check-nftfw-db](exim4/sympl.d/10-acl/10-acl-check-connect/30-check-nftfw-db)
```

## Exim - ch7 - Ratelimiting connections

Exim can ratelimit connections, and generally the only sites that 'legally' send mail very quickly at your machine are known relays, and we've carefully excluded them from these checks. The others are usually spammers or exhaustive decrypters that connect at full bore. The ratelimit provided by this rule doesn't block transgressors, so legal email sites will pick up and start again. It's not that draconian - 10 messages every 15 minutes. It's worth doing, because it generally gives the firewall scanning code time to evaluate the nastiness of the connection, so often when the nasties return they are blocked.

The new file is:

``` sh
[exim4/sympl.d/10-acl/10-acl-check-connect/50-ratelimit](exim4/sympl.d/10-acl/10-acl-check-connect/50-ratelimit)
```


