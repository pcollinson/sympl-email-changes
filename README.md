# sympl-email-changes - changes to Sympl buster email installation

This repository contains the changes I make to the ```exim4``` and ```dovecot``` installations on Sympl for Buster. My intention is to provide a better signature of malicious activity in log files, so the firewall generation system can pick up bad IPs and do something about them. The setup has been running for some years on a Symbiosis system and helps to pick up attempts at exhaustive password decryption amongst other things. I'm moving from the distributed files and inserting files from a running installation. My intention is to allow you to understand what the changes do, and also to allow you to skip a step, if you don't think that it is necessary for you.

I am starting from the configuration files supplied with Sympl as of 29/April/2020. The ```dovecot``` and ```exim4``` directories are installed without cloning, because there is no mileage in having the whole sympl installation replicated here. I'm altering the set of files step by step with a git commit at every stage. This file supplies a description of what each change does.

Changes all affect files in the ```sympl.d``` directory in ```/etc/dovecot``` or ```/etc/exim4```. Change the files, then run ```make``` in the relevant directory to install the alterations.

## Dovecot - ch1

I want Dovecot to tell me when failed attempts are made to verify identities. It will do this, but it's not available in the installation. The configuration setting:

``` sh
# Log unsuccessful authentication attempts and the reasons why they failed.
auth_verbose = yes

```
is needed. I've raided the standard distribution to place all the authorisation variables into one file because they are useful to have, and installed the file in:

``` sh
/etc/dovecot/sympl.d/10-main/35-log-debug
```

## Dovecot - ch2

My machine is not public, in the sense that everyone using it is known and so it's good to move the standard imap ports to somewhere else, which helps to defeat the robot attempts from script-kiddies. I remove pop access from the firewall, but a similar setup can be installed. If you are using ```roundcube``` then the standard ports need to be available, but only need to be active for ```localhost```. Again this file is missing from the standard Sympl distribution and I include it to assist you to do this. Look at the file, you'll need to supply your own private port numbers - replace ```YOUR PORT``` by two numbers.

The new file is

``` sh
/etc/dovecot/sympl.d/10-main/15-imap-ports
```

