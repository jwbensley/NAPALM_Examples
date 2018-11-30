
## Overview

This script is used to check the syntax of device configurations before  
they are applied.

#### [syntax_check.py](syntax_check.py)

This script performs basic checks against IOS and Junos config files. The  
checks are simple syntactic and semantic checks for example, that an IP  
address is valid or that a VLAN ID isn't larger than 4095. The script expects  
the config files to be commands written down exactly as you would enter them  
into the CLI. For IOS this means CLI commands as they would be entered on the  
CLI or as shown in output from `show run` for example. For Junos this means  
the `set` form of commands or output from `show configuration | display set`.

The script currently supports checking IOS and Junos files however, checking  
Junos files is almost pointless because, entering invalid commands such as an  
invalid IP address into the Junos CLI is difficult. Junos is very good at  
checking user input, but it isn't perfect. IOS however, performs no input  
validation at all and is terrible.

Currently the script supports more IOS based checks that Junos, but in either  
case more checks should be added.

IOS syntax checks:

* Check bridge-domain/VLAN number
* Check BGP neighbour IPv4/IPv6 address is valid
* Check interface description follows standard
* Check IPv4 helper address is valid
* Check interface IPv4/IPv6 address is valid
* CHeck IOS router ID is valid IPv4 address
* Check IS-IS NET address is valid
* Check VRF RD is valid IPv4 address + VPN ID
* Check VRF RT is valid

Junos syntax checks:

* Check bridge-domain number is valid
* Check interface description follows standard
* Check interface VLAN ID is valid
* Check interface IPv4/IPv6 address is valid

Some example bad output is bundles with the script to verify each check the  
script is making works.  

Example output:
```bash
bensley@LT-10383(syntax_check)$./syntax_check.py -c bad_configs/merge_config_junos.txt -t junos
Syntax checking: bad_configs/merge_config_junos.txt
Invalid interface description format: set interfaces xe-9/9/9 description "link to your mum"
Invalid IPv4 address: set interfaces xe-9/9/9 unit 0 family inet address 10.20.300.44/24
Invalid IPv4 address: set interfaces xe-9/9/9 unit 0 family inet address 10.0.1/30
Invalid IPv4 subnet mask: set interfaces xe-9/9/9 unit 0 family inet address 10.100.0.1/33
Invalid IPv6 address: set interfaces xe-9/9/9 unit 0 family inet6 address xyz::1/64
Invalid IPv6 subnet mask: set interfaces xe-9/9/9 unit 0 family inet6 address fe::1/129
Invalid VLAN ID: set interfaces xe-9/9/9 unit 10 vlan-id 4096
Invalid VLAN ID: set interfaces xe-9/9/9 unit 10 vlan-id 0
Invalid VLAN ID: set interfaces xe-9/9/9 unit 10 vlan-id a
Config file failed checks

bensley@LT-10383(syntax_check)$./syntax_check.py -c good_configs/merge_config_junos.txt -t junos
Syntax checking: good_configs/merge_config_junos.txt
Config passed without issue

bensley@LT-10383(syntax_check)$./syntax_check.py -c bad_configs/merge_config_ios.txt -t ios
Syntax checking: bad_configs/merge_config_ios.txt
Invalid IPv4 address: ip address 10.20.300.44 255.255.255.0
Invalid IPv4 address: ip address 10.0.1 255.255.255.0
Invalid IPv4 subnet mask: ip address 10.100.0.1 255.255.2555.0
Invalid IPv4 subnet mask: ip address 10.100.0.1 255.255.256.0
Invalid IPv6 address: ipv6 address xyz::1/64
Invalid IPv6 subnet mask: ipv6 address fe::1/129
Invalid route distinguisher: rd 1.2.3.999:100
Invalid route distinguisher: rd 1.2.3.4:65536
Invalid route-target: route-target both 65536:65536
Invalid route-target: route-target both 4294967296:1
Invalid route-target: route-target both 1:4294967296
Config file failed checks

bensley@LT-10383(syntax_check)$./syntax_check.py -c good_configs/merge_config_ios.txt -t ios
Syntax checking: good_configs/merge_config_ios.txt
Config passed without issue
```
