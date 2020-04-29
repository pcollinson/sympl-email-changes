# sympl-email-changes - changes to Sympl buster email installation

This repository contains the changes I make to the ```exim4``` and ```dovecot``` installations on Sympl for Buster. My intention is to provide a better signature of malicious activity in log files, so the firewall generation system can pick up bad IPs and do something about them. The setup has been running for some years on a Symbiosis system and helps to pick up attempts at exhaustive password decryption amongst other things. I'm moving from the distributed files and inserting files from a running installation. My intention is to allow you to understand what the changes do, and also to allow you to skip a step, if you don't think that it is necessary for you.

I am starting from the configuration files supplied with Sympl as of 29/April/2020. The ```dovecot``` and ```exim4``` directories are installed without cloning, because there is no mileage in having the whole sympl installation replicated here. I'm altering the set of files step by step with a git commit at every stage. This file supplies a description of what each change does.

Changes all affect files in the ```sympl.d``` directory in ```/etc/dovecot``` or ```/etc/exim4```. Change the files, then run ```make``` in the relevant directory to install the alterations.


