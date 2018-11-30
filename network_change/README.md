## Overview

This script is used to automate basic network configurations.

#### [network_change.py](network_change.py)

This script automates an example network configuration process. It performs  
the following list of actions in order:  

* Syntax check the config to be applied to each device (basic IOS and Junos checks)
* Check if any devices have active alarms on SolarWinds using the API
* Checkout the network changes git repo
* Record the pre-change state of each device
* Apply the config to each device
* Record the post-change state of each device
* Generate a diff of the pre and post device state
* Check if any devices have a different alarm severity on SolarWinds from before the change
* Commit and push everything to the git repo

This script is essentially a wrapper for the other scripts in this repo.  
It calls the other scripts to run the pre/post checks and apply configuration  
etc. To use it simply place it in your PATH variable.

```bash
bensley@LT-10383(network_change)$pwd
/home/bensley/Scripting/Python/NAPALM/network_change

bensley@LT-10383(network_change)$cd /home/bensley/Changes/scripted_changes/
bensley@LT-10383(scripted_changes)$PATH="$PATH:/home/bensley/Scripting/Python/NAPALM/network_change"
```

The script expects either an `inventory.yml` file or a single host. When  
using an `inventory.yml` file one provides a list of devices you want to push  
the same configuration too. You can specify one config file per device type.  
For example, to push a new VRF to all PEs create a file with the new VRF  
config in Junos syntax and another file in IOS syntax etc. The script will  
apply the config to all devices of the same type as the config file.  

To apply unique config to each host create a per-host config file and run the  
script in target mode.  

Below is an example folder structure, commands and config for a push to all  
devices of the same type:  

```bash
bensley@LT-10383(scripted_changes)$tree
.
├── checks
│   ├── checks_ios.txt
│   ├── checks_junos.txt
│   └── diff_filter.yml
├── configs
│   ├── merge_config_ios.txt
│   └── merge_config_junos.txt
└── inventory.yml

bensley@LT-10383(scripted_changes)$head checks/checks_ios.txt
term mon
term len 0
term exec prompt timestamp
show ver
show proc cpu sort
show proc cpu hist
show proc mem sort

$head configs/merge_config_junos.txt
set system time-zone Europe/London

bensley@LT-10383(scripted_changes)$head configs/merge_config_ios.txt
login on-failure log
login on-success log

bensley@LT-10383(scripted_changes)$cat inventory.yml
# vMX
R2:
  hostname: 192.168.223.12
  os: junos
  username: napalm
# CSR1000v
R3-IOSXE:
  hostname: 192.168.223.13
  os: ios
  username: napalm
```

Below is an example of using the script, it runs through the entire change  
process, checking config syntax, checking SolarWinds, checking out the change  
git repo, recording the device pre-change state (into the repo), apply the  
config changes (logged in the repo), recording the device post-change state  
(into the repo), checking SolarWinds for different alarms and finally  
committing all the logs back to the change repo:
```bash
bensley@LT-10383(scripted_changes)$network_change.py -ref INC000123 -v
Default password:
Loading inventory inventory.yml
Loaded 2 device(s) in inventory
All config syntax checks have passed.

Created directory: ./network-changes//INC000123/
Created directory: ./network-changes//INC000123//pre
Created directory: ./network-changes//INC000123//config
Created directory: ./network-changes//INC000123//post
Created directory: ./network-changes//INC000123//diff

Checking SolarWinds for active alarms on inventory devices...
SolarWinds username: james.bensley
SolarWinds password:
No active alarms on SolarWinds for change device(s)

Cloning/pulling git change repo to ./network-changes/...
Initialized empty Git repository in /home/bensley/Changes/scripted_changes/network-changes/.git/
Username for 'https://git.example.com': james.bensley
Password for 'https://james.bensley@git.example.com':
remote: Enumerating objects: 305, done.
remote: Counting objects: 100% (305/305), done.
remote: Compressing objects: 100% (237/237), done.
remote: Total 305 (delta 142), reused 96 (delta 49)
Receiving objects: 100% (305/305), 184.89 KiB | 0 bytes/s, done.
Resolving deltas: 100% (142/142), done.
From https://git.example.com/james.bensley/network-changes
 * branch            master     -> FETCH_HEAD
 * [new branch]      master     -> origin/master
HEAD is now at b91018f change: CR-Test-IOSXE

Ready to record pre-change device state? [yes/no]: yes
Trying 192.168.223.12...
Created directory: ./network-changes//INC000123//pre//192.168.223.12
192.168.223.12 done
Trying 192.168.223.13...
Created directory: ./network-changes//INC000123//pre//192.168.223.13
192.168.223.13 done

All state outputs have been gathered.

Ready to apply config to devices? [yes/no]: yes

Trying 192.168.223.12...
Loaded merge config
192.168.223.12 diff:
[edit system]
+  time-zone Europe/London;
Commit check passed on 192.168.223.12
Merging config...
Merged
192.168.223.12 done

Trying 192.168.223.13...
Loaded merge config
192.168.223.13 diff:
+login on-failure log
+login on-success log
Merging config...
Output: 44 bytes copied in 0.069 secs (638 bytes/sec)
Merged
192.168.223.13 done
Config applied to all devices without issue.

Ready to record post-change device state? [yes/no]: yes
Trying 192.168.223.13...
Created directory: ./network-changes//INC000123//post//192.168.223.13
192.168.223.13 done
Trying 192.168.223.12...
Created directory: ./network-changes//INC000123//post//192.168.223.12
192.168.223.12 done

All state outputs have been gathered.
Comparing ./network-changes//INC000123//pre//192.168.223.13 to ./network-changes//INC000123//post/192.168.223.13...
done
Comparing ./network-changes//INC000123//pre//192.168.223.12 to ./network-changes//INC000123//post/192.168.223.12...
done

Checking SolarWinds for active alarms on inventory devices...
SolarWinds username: james.bensley
SolarWinds password:
No active alarms on SolarWinds for change device(s)

Ready to commit change to git? [yes/no]: yes
Commit git changes to repo...
[master fde866c] change: INC000123
 168 files changed, 11281 insertions(+)
 create mode 100644 INC000123/config/192.168.223.12_2018-11-30--14-29-22.txt
 create mode 100644 INC000123/config/192.168.223.13_2018-11-30--14-32-25.txt
 create mode 100644 INC000123/diff/192.168.223.12.diff
 create mode 100644 INC000123/diff/192.168.223.13.diff
 create mode 100644 INC000123/post/192.168.223.12/file list detail vartmp  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/set cli timestamp.txt
 create mode 100644 INC000123/post/192.168.223.12/show bfd session  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show bfd session summary  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show bgp summary  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show chassis alarms  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show chassis environment  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show chassis fpc  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show chassis hardware detail  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show chassis routing-engine  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show configuration  display set  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show configuration  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show interfaces descriptions  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show interfaces terse routing-instance all  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show isis adjacency  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show isis interface  no more.txt
 create mode 100644 INC000123/post/192.168.223.12/show krt queue  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show ldp interface  no more.txt
 create mode 100644 INC000123/post/192.168.223.12/show ldp session  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show log messages  last 200  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show mpls interface  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show ospf interface  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show ospf neighbor  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show pfe statistics error  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show pfe statistics traffic  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show route forwarding-table summary  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show route forwarding-table summary family inet  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show route forwarding-table summary family inet6  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show route summary  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show rsvp interface  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show rsvp neighbor  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system alarms  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system boot-messages  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system commit  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system memory  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system memory  no-more.txt.tmp
 create mode 100644 INC000123/post/192.168.223.12/show system processes brief  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system processes extensive  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system queues  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system resource-monitor summary.txt
 create mode 100644 INC000123/post/192.168.223.12/show system storage  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show system virtual-memory  no-more.txt
 create mode 100644 INC000123/post/192.168.223.12/show version  no-more.txt
 create mode 100644 INC000123/post/192.168.223.13/show bfd neighbors.txt
 create mode 100644 INC000123/post/192.168.223.13/show bfd summary.txt
 create mode 100644 INC000123/post/192.168.223.13/show bgp all summary.txt
 create mode 100644 INC000123/post/192.168.223.13/show bgp ipv4 unicast summary  begin Neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show bgp l2vpn vpls all summary  begin Neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show bgp vpnv4 unicast all summary  begin Neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show bridge-domain  exclude DYNAMIC.txt
 create mode 100644 INC000123/post/192.168.223.13/show bridge-domain.txt
 create mode 100644 INC000123/post/192.168.223.13/show clns interface.txt
 create mode 100644 INC000123/post/192.168.223.13/show int desc.txt
 create mode 100644 INC000123/post/192.168.223.13/show inventory.txt
 create mode 100644 INC000123/post/192.168.223.13/show ip ospf interface brief.txt
 create mode 100644 INC000123/post/192.168.223.13/show ip ospf neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show ip pim interface.txt
 create mode 100644 INC000123/post/192.168.223.13/show ip pim neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show ip rsvp interface.txt
 create mode 100644 INC000123/post/192.168.223.13/show ip rsvp neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show isis neighbors.txt
 create mode 100644 INC000123/post/192.168.223.13/show l2vpn service all.txt
 create mode 100644 INC000123/post/192.168.223.13/show logging.txt
 create mode 100644 INC000123/post/192.168.223.13/show mpls ldp discovery.txt
 create mode 100644 INC000123/post/192.168.223.13/show mpls ldp neighbor.txt
 create mode 100644 INC000123/post/192.168.223.13/show proc cpu hist.txt
 create mode 100644 INC000123/post/192.168.223.13/show proc cpu sort.txt
 create mode 100644 INC000123/post/192.168.223.13/show proc cpu sort.txt.tmp
 create mode 100644 INC000123/post/192.168.223.13/show proc mem sort.txt
 create mode 100644 INC000123/post/192.168.223.13/show proc mem sort.txt.tmp
 create mode 100644 INC000123/post/192.168.223.13/show processes cpu platform sorted.txt
 create mode 100644 INC000123/post/192.168.223.13/show processes cpu platform sorted.txt.tmp
 create mode 100644 INC000123/post/192.168.223.13/show processes memory platform sorted.txt
 create mode 100644 INC000123/post/192.168.223.13/show processes memory platform sorted.txt.tmp
 create mode 100644 INC000123/post/192.168.223.13/show standby  inc last.txt
 create mode 100644 INC000123/post/192.168.223.13/show standby brief.txt
 create mode 100644 INC000123/post/192.168.223.13/show ver.txt
 create mode 100644 INC000123/post/192.168.223.13/show vfi.txt
 create mode 100644 INC000123/post/192.168.223.13/show xconnect all.txt
 create mode 100644 INC000123/post/192.168.223.13/term exec prompt timestamp.txt
 create mode 100644 INC000123/post/192.168.223.13/term len 0.txt
 create mode 100644 INC000123/post/192.168.223.13/term mon.txt
 create mode 100644 INC000123/pre/192.168.223.12/file list detail vartmp  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/set cli timestamp.txt
 create mode 100644 INC000123/pre/192.168.223.12/show bfd session  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show bfd session summary  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show bgp summary  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show chassis alarms  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show chassis environment  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show chassis fpc  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show chassis hardware detail  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show chassis routing-engine  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show configuration  display set  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show configuration  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show interfaces descriptions  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show interfaces terse routing-instance all  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show isis adjacency  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show isis interface  no more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show krt queue  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show ldp interface  no more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show ldp session  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show log messages  last 200  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show mpls interface  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show ospf interface  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show ospf neighbor  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show pfe statistics error  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show pfe statistics traffic  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show route forwarding-table summary  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show route forwarding-table summary family inet  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show route forwarding-table summary family inet6  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show route summary  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show rsvp interface  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show rsvp neighbor  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system alarms  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system boot-messages  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system commit  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system memory  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system memory  no-more.txt.tmp
 create mode 100644 INC000123/pre/192.168.223.12/show system processes brief  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system processes extensive  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system queues  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system resource-monitor summary.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system storage  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show system virtual-memory  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.12/show version  no-more.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bfd neighbors.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bfd summary.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bgp all summary.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bgp ipv4 unicast summary  begin Neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bgp l2vpn vpls all summary  begin Neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bgp vpnv4 unicast all summary  begin Neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bridge-domain  exclude DYNAMIC.txt
 create mode 100644 INC000123/pre/192.168.223.13/show bridge-domain.txt
 create mode 100644 INC000123/pre/192.168.223.13/show clns interface.txt
 create mode 100644 INC000123/pre/192.168.223.13/show int desc.txt
 create mode 100644 INC000123/pre/192.168.223.13/show inventory.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ip ospf interface brief.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ip ospf neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ip pim interface.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ip pim neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ip rsvp interface.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ip rsvp neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show isis neighbors.txt
 create mode 100644 INC000123/pre/192.168.223.13/show l2vpn service all.txt
 create mode 100644 INC000123/pre/192.168.223.13/show logging.txt
 create mode 100644 INC000123/pre/192.168.223.13/show mpls ldp discovery.txt
 create mode 100644 INC000123/pre/192.168.223.13/show mpls ldp neighbor.txt
 create mode 100644 INC000123/pre/192.168.223.13/show proc cpu hist.txt
 create mode 100644 INC000123/pre/192.168.223.13/show proc cpu sort.txt
 create mode 100644 INC000123/pre/192.168.223.13/show proc cpu sort.txt.tmp
 create mode 100644 INC000123/pre/192.168.223.13/show proc mem sort.txt
 create mode 100644 INC000123/pre/192.168.223.13/show proc mem sort.txt.tmp
 create mode 100644 INC000123/pre/192.168.223.13/show processes cpu platform sorted.txt
 create mode 100644 INC000123/pre/192.168.223.13/show processes cpu platform sorted.txt.tmp
 create mode 100644 INC000123/pre/192.168.223.13/show processes memory platform sorted.txt
 create mode 100644 INC000123/pre/192.168.223.13/show processes memory platform sorted.txt.tmp
 create mode 100644 INC000123/pre/192.168.223.13/show standby  inc last.txt
 create mode 100644 INC000123/pre/192.168.223.13/show standby brief.txt
 create mode 100644 INC000123/pre/192.168.223.13/show ver.txt
 create mode 100644 INC000123/pre/192.168.223.13/show vfi.txt
 create mode 100644 INC000123/pre/192.168.223.13/show xconnect all.txt
 create mode 100644 INC000123/pre/192.168.223.13/term exec prompt timestamp.txt
 create mode 100644 INC000123/pre/192.168.223.13/term len 0.txt
 create mode 100644 INC000123/pre/192.168.223.13/term mon.txt
Username for 'https://git.example.com': james.bensley
Password for 'https://james.bensley@git.example.com':
Counting objects: 120, done.
Delta compression using up to 8 threads.
Compressing objects: 100% (119/119), done.
Writing objects: 100% (120/120), 85.09 KiB | 0 bytes/s, done.
Total 120 (delta 40), reused 3 (delta 0)
remote: Resolving deltas: 100% (40/40), completed with 1 local object.
To https://git.example.com/james.bensley/network-changes.git
   b91018f..fde866c  master -> master

All done!
```

Below a rollback is made - this will rollback the single most recent config  
change pushed through NAPALM:
```bash
bensley@LT-10383(scripted_changes)$network_change.py -ref INC000123 -rollback
Default password:
Loading inventory inventory.yml
Loaded 2 device(s) in inventory

Performing rollback...
Trying 192.168.223.12...
192.168.223.12 rolled back
192.168.223.12 done
Trying 192.168.223.13...
192.168.223.13 Total number of passes: 1
Rollback Done
192.168.223.13 done
All done!
```