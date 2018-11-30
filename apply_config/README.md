
## Overview

These example scripts show how to apply config to devices using NAPALM and  
also the importance of config syntax and semantic checking.  

* [apply_config.py](#apply_configpy)
* [Config Checking](#config-checking)


#### [apply_config.py](apply_config.py)
This script applies config stored in a text file to a list of devices stored  
in an inventory file. For IOS/IOS-XE/IOS-XR devices SCP must be explicitly  
enabled. For Junos simply having SSH enabled is sufficient enough.  

The config is either merged with the existing running config in which case a  
partial configuration can be supplied. Alternatively, a full configuration  
replace operation can be applied in which case a full device configuration  
should be supplied.

The config to be applied should be stored in a file the name of which  
describes the configuration operation and device type. The format is 'merge'  
or 'replace' `_config_` + os + `.txt`, e.g. `merge_config_ios.txt` or  
`merge_config_junos.txt` to merge a partial configuration with the existing  
running device configuration. A full replacement configuration would be  
stored in `replace_config_ios.txt` or `replace_config_junos.txt`. A merge  
operation is the default mode, a full replace requires the `--replace` CLI  
option. This allows for batch committing the same configuration to a group of  
network devices, for example pushing a new ACL.

To perform a merge or replace operation on a per-device basis with a  
per-device configuration file, create a text file in the config directory  
which has the device hostname + `.txt` as the filename. E.g. `router1.txt`.  
Batch config mode is the default mode, per-host config mode is enabled with  
the `--host` CLI option. The script merges a partial config by default, to  
perform a full configuration replace operation in per-host config mode, as  
above, use the `--replace` CLI option.

The script can be run against a single host / target using the `-t` option.  
This ignores the `-i` option and any inventory file present. When using `-t`  
the `-o` option must be specified so that NAPALM knows the device OS type.  
Also when using the `-t` option the `-c` option points at a config file, not  
a directory of config files.

&nbsp;

For Cisco IOS/IOS-XE/IOS-XR the config should be as one would enter it into the 
CLI, e.g.
```
interface Gi0/1
 no shut
 description Your Suck
```
For Junos devices the config must be in the `set` format, e.g.
```
set interfaces ge-0/0/1 description "You Suck"
```

&nbsp;

The following example output shows a dry-run merge operation being run against 
an IOS-XE and Junos device:
```bash
bensley@LT-10383(apply_config)$./apply_config.py -d -v
Default password:
Path to output logging directory doesn't exist: ./logs/
Created directory: ./logs/
Dry run enabled!

Trying R3-IOSXE...
Loaded merge config
R3-IOSXE diff:
+int gi3
- no shut
+ description csr1000v-gi3:vmx-ge-0/0/2
+ ip address 10.0.23.3 255.255.255.0
R3-IOSXE done

Trying R2-Junos...
Loaded merge config
R2-Junos diff:
[edit interfaces ge-0/0/2]
-   description test-description;
+   description vMX-ge-0/0/2:csr1000v-gi3;
Commit check passed on R2-Junos
R2-Junos done
```

The following output shows the config being pushed to the Juniper device only 
with a commit message that is the change reference number:
```bash
bensley@LT-10383(apply_config)$./apply_config.py -o junos -n "CR12345"
Default password:

Trying R2-Junos...
Loaded merge config
R2-Junos diff:
[edit interfaces ge-0/0/2]
-   description test-description;
+   description vMX-ge-0/0/2:csr1000v-gi3;
Merging config...
Merged
R2-Junos done
```

```bash
bensley@LT-10383(apply_config)$cat logs/R2-Junos_2018-11-07--11-27-45.txt
#R2-Junos
[edit interfaces ge-0/0/2]
-   description test-description;
+   description vMX-ge-0/0/2:csr1000v-gi3;
```

&nbsp;

### Config Checking
It is important to note that Cisco's IOS has virtually no syntax or semantic 
checking when trying to generate a diff for a config replace/merge, whereas 
Juniper's Junos has both. In each of the following examples Junos throws an 
error when trying enter the following config into the CLI and also when using 
`commit check` (and thus `commit` too), whereas IOS reports no errors and in 
every case tries to apply the config.

&nbsp;

Config which is syntactically correct but semantically incorrect 
(shelf/slot/interface x/x/x/x/x/x doesn't exist):
```
interface Gi1/1/1/1/1/1
 description "invalid name"
```
IOS produces the following diff:
```
+interface Gi1/1/1/1/1/1
+ description "invalid name"
```

&nbsp;

Config which is both syntactically and semantically correct but still incorrect (interfaces on this device as Gi1-Gi4 meaning non-existing interface):
```
interface Gi100000
 ip address 10.20.30.44 255.255.255.0
```
IOS produces the following diff:
```
+interface Gi100000
+ ip address 10.20.30.44 255.255.255.0
```

&nbsp;

Config which is syntactically correct but semantically incorrect (invalid IPv4 address):
```
interface Gi1
 ip address 10.20.300.44 255.255.255.0
```
IOS produces the following diff:
```
+interface Gi1
+ ip address 10.20.300.44 255.255.255.0
```

&nbsp;

Config which is syntactically incorrect but semantically correct (invalid `interface` command):
```
interfe Gi1
 ip address 10.20.30.44 255.255.255.0
```
IOS produces the following diff:
```
+interfe Gi1
+ ip address 10.20.30.44 255.255.255.0
```

&nbsp;

Equivalent Junos config and errors (in above order):
```
set interfaces xe-9/9/9/9 description "invalid interface name"

"fpc value outside range 0..0 for '9/9/9/9' in 'xe-9/9/9/9'"
```
```
set interfaces ge-5/5/5 unit 0 family inet address 10.20.30.44/24

"fpc value outside range 0..0 for '5/5/5"
```
```
set interfaces ge-0/0/4 unit 0 family inet address 10.20.300.44/24

"syntax error"
```
```
set interfe ge-0/0/4 unit 0 family inet address 10.20.30.44/24

"syntax error"
```
