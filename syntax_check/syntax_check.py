#!/usr/bin/python3

"""
Perform a syntax check against a specified config file.
"""

import argparse
import os
import re
import socket
import sys


def check_file_exists(cfg_file):

    if not os.path.isfile(cfg_file):
        print("Host config file {} doesn't exist".format(cfg_file))
        sys.exit(1)


def check_ios_bd(cfg_line):

    bd = cfg_line.split()[1] # "100"
    if not is_valid_bd(bd):
        print("Invalid bridge-domain: {}".format(cfg_line))
        return False

    return True


def check_ios_bgp_neigh_addr(cfg_line):

    # Crude IPv4/IPv6 test..

    # Is IPv4
    if len(cfg_line.split(".")) > 1:

        # "neighbor 10.0.0.1"
        ipv4_neigh = cfg_line.split()[1] # "10.0.0.1"
        if not is_valid_ipv4_address(ipv4_neigh):
            print("Invalid IPv4 BGP neighbour address: {}".format(cfg_line))
            return False
        
        else:
            return True

    # Is IPv6
    else:

        # "neighbor 1::1:2:3:4"
        ipv6_neigh = cfg_line.split()[1] # "1::1:2:3:4"
        if not is_valid_ipv4_address(ipv6_neigh):
            print("Invalid IPv6 BGP neighbour address: {}".format(cfg_line))
            return False
        
        else:
            return True


def check_ios_int_desc(cfg_line):

    int_desc = cfg_line.split()[1] # "core|CORE-LD4-PE1|xe-2/2/8|Carrier1|C1234|10G|DWDM wave via Ciena"
    if not is_valid_int_desc(int_desc):
        print("Invalid interface description format: {}".format(cfg_line))
        return False

    return True


def check_ios_int_ipv4_helper(cfg_line):

    ipv4_helper = cfg_line.split()[2] # "10.0.0.1"
    if not is_valid_ipv4_address(ipv4_helper):
        print("Invalid IPv4 helper address: {}".format(cfg_line))
        return False

    return True


def check_ios_int_ipv4(cfg_line):

    ret_val = True

    ipv4_addr = cfg_line.split()[2] # "10.0.0.1"
    if not is_valid_ipv4_address(ipv4_addr):
        print("Invalid IPv4 address: {}".format(cfg_line))
        ret_val = False

    try:
        # Check dotted subnet mask
        ipv4_mask = cfg_line.split()[3] # "255.255.255.0"
        if not is_valid_ipv4_mask(ipv4_mask, dotted=True):
            print("Invalid IPv4 subnet mask: {}".format(cfg_line))
            ret_val = False
    except:

        try:
            # Check CIDR subnet mask
            ipv4_mask = cfg_line.split()[2].split("/")[1] # "24"
            if not is_valid_ipv4_mask(ipv4_mask, dotted=False):
                print("Invalid IPv4 subnet mask: {}".format(cfg_line))
                ret_val = False
        except:
            ret_val = False

    return ret_val


def check_ios_int_ipv6(cfg_line):

    ret_val = True

    ipv6_addr = cfg_line.split()[2].split("/")[0] # "a:b:c:d::1"
    if not is_valid_ipv6_address(ipv6_addr):
        print("Invalid IPv6 address: {}".format(cfg_line))
        ret_val = False

     # Check CIDR subnet mask
    try:
        ipv6_mask = cfg_line.split()[2].split("/")[1] # "64"
        if not is_valid_ipv6_mask(ipv6_mask):
            print("Invalid IPv6 subnet mask: {}".format(cfg_line))
            ret_val = False
    except:
        ret_val = False

    return ret_val


def check_ios_rid(cfg_line):

    # Crude IPv4/IPv6 test..

    # Is IPv4
    if len(cfg_line.split(".")) > 1:

        # Try OSPF: "router-id 10.0.0.1"
        ipv4_rid = cfg_line.split()[1] # "10.0.0.1"
        if is_valid_ipv4_address(ipv4_rid):
            return True

         # Try BGP: "bgp router-id 10.0.0.1"
        else:
            ipv4_rid = cfg_line.split()[2] # "10.0.0.1"
            if is_valid_ipv4_address(ipv4_rid):
                return True
            else:
                print("Invalid IPv4 router ID: {}".format(cfg_line))
                return False
    
    # Is IPv6
    else:

        # Try BGP: "bgp router-id 1::2:3:4:5"
        ipv6_rid = cfg_line.split()[1] # OSPF "10.0.0.1"
        if not is_valid_ipv6_address(ipv6_rid):
            print("Invalid IPv6 router ID: {}".format(cfg_line))
            return False
        
        else:
            return True


def check_ios_isis_net(cfg_line):
    
    isis_net = cfg_line.split()[1] # "49.0001.0101.0500.0192.00"
    if not is_valid_isis_nsap(isis_net):
        print("Invalid ISIS NET: {}".format(cfg_line))
        return False

    return True


def check_ios_vrf_rd(cfg_line):


    rd = cfg_line.split()[1] # "10.0.0.1:100"
    if not is_valid_rd(rd):
        print("Invalid route distinguisher: {}".format(cfg_line))
        return False

    return True


def check_ios_vrf_rt(cfg_line):

    rt = cfg_line.split()[2] # "123:456"
    if not is_valid_rt(rt):
        print("Invalid route-target: {}".format(cfg_line))
        return False

    return True


def check_junos_bd_vlan_id(cfg_line):

    vlan_id = cfg_line.split()[4] # "100"
    if not is_valid_bd(vlan_id):
        print("Invalid bridge-domain VLAN ID: {}".format(cfg_line))
        return False

    return True


def check_junos_int_desc(cfg_line):

    int_desc = cfg_line.split("description")[1] # "core|CORE-LD4-PE1|xe-2/2/8|Carrier1|C1234|10G|DWDM wave via Ciena"
    if not is_valid_int_desc(int_desc):
        print("Invalid interface description format: {}".format(cfg_line))
        return False

    return True


def check_junos_int_vlan_id(cfg_line):

    vlan_id = cfg_line.split()[6] # "100"
    if not is_valid_bd(vlan_id):
        print("Invalid VLAN ID: {}".format(cfg_line))
        return False

    return True


def check_junos_int_ipv4(cfg_line):

    ret_val = True

    ipv4_addr = cfg_line.split()[8].split("/")[0] # "10.0.0.1"
    if not is_valid_ipv4_address(ipv4_addr):
        print("Invalid IPv4 address: {}".format(cfg_line))
        ret_val = False

    try:
        # Check CIDR subnet mask
        ipv4_mask = cfg_line.split()[8].split("/")[1] # "24"
        if not is_valid_ipv4_mask(ipv4_mask, dotted=False):
            print("Invalid IPv4 subnet mask: {}".format(cfg_line))
            ret_val = False
    except:
        ret_val = False

    return ret_val


def check_junos_int_ipv6(cfg_line):

    ret_val = True

    ipv6_addr = cfg_line.split()[8].split("/")[0] # "a:b:c:d::1"
    if not is_valid_ipv6_address(ipv6_addr):
        print("Invalid IPv6 address: {}".format(cfg_line))
        ret_val = False

     # Check CIDR subnet mask
    try:
        ipv6_mask = cfg_line.split()[8].split("/")[1] # "64"
        if not is_valid_ipv6_mask(ipv6_mask):
            print("Invalid IPv6 subnet mask: {}".format(cfg_line))
            ret_val = False
    except:
        ret_val = False

    return ret_val


def is_valid_bd(bd):

    if not bd.isdigit():
        return False

    if (int(bd) > 4095) or (int(bd) < 1):
        return False


    return True


def is_valid_int_desc(int_desc):

    # The format used is 6 fields seperated by a vertical pipe
    # "link_type|remote_device_hostname|remote_interface_name|circuit_provider|circuit_ref|circuit_speed|free_text"
    desc = r"(.*\|){6}"
    if not re.search(desc, int_desc):
        return False

    return True


def is_valid_ipv4_address(address):

    try:
        socket.inet_pton(socket.AF_INET, address)
    except AttributeError:  # no inet_pton
        try:
            socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:  # not a valid address
        return False

    return True


def is_valid_ipv4_mask(mask, dotted=True):

    # 255.255.255.0
    if dotted:

        octets = mask.split(".")

        # Not exactly four octects
        if len(octets) != 4:
            return False

        for octet in octets:

            # Any octect is larger than 255 or lower than 0
            if (int(octet) > 255) or (int(octet) < 0):
                return False

            # Any octect length is more then 3
            if len(str(octet)) > 3:
                return False

    # 24
    else:

        if (int(mask) > 32) or (int(mask) < 0):
            return False


    return True


def is_valid_ipv6_address(address):

    try:
        socket.inet_pton(socket.AF_INET6, address)
    except socket.error:  # not a valid address
        return False
    return True


def is_valid_ipv6_mask(mask):

    if (int(mask) > 128) or (int(mask) < 0):
        return False

    return True


def is_valid_isis_nsap(net):

    # Assume NSAP starts with 49 for private areas and ends with either 
    # .00 or .0000
    NSAP = r"49\.[0-9][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9]\.[0-9][0-9][0-9][0-9]\.(00$|0000$)"

    if not re.search(NSAP, net):
        return False

    return True


def is_valid_rd(rd):

    '''
    Assume we are using Type 1 RDs,
    32bit dotted decimal (IPv4) : Assigned Number
    '''

    try:
        ip = rd.split(":")[0]
        num = rd.split(":")[1]
    except:
        return False

    if not is_valid_ipv4_address(ip):
        return False

    if not num.isdigit():
        return False

    if (int(num) > 65535) or (int(num) < 0):
        return False

    return True


def is_valid_rt(rt):

    '''
    Assuming ASN:community encoding, we have 6 bytes in total
    2 bytes : 4 bytes
    or
    4 bytes : 2 bytes
    '''

    try:
        asn = rt.split(":")[0]
        com = rt.split(":")[1]
    except:
        return False

    if not asn.isdigit():
        return False

    if not com.isdigit():
        return False

    if (int(asn) < 0) or (int(com) < 0):
        return False

    if (int(asn) > 4294967295):
        return False

    if (int(asn) > 65535): # 4 bytes : 2 bytes
        if (int(com) > 65535):
            return False

    else: # 2 bytes : 4 bytes
        if (int(com) > 4294967295):
            return False

    return True


def parse_cli_args():

    parser = argparse.ArgumentParser(
        description='Perform a syntax check against a config file',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '-c', '--config-file',
        help='Config file to check.',
        type=str,
        default=None,
        required=True
    )
    parser.add_argument(
        '-t', '--type',
        help='The device type of the config file being checked (use NAPALM '
             'types e.g. junos, ios).',
        type=str,
        default=None,
        required=True
    )

    return vars(parser.parse_args())


def validate_ios_config(config):

    ret_val = True

    IOS_BD = r"bridge- "
    IOS_BGP_NEIGH_ADDR = r"nei "
    IOS_INT_DESC = r" des"
    IOS_IPV4_ADDRESS = r"ip addr"
    IOS_IPV4_HELPER = r"ip help"
    IOS_IPV6_ADDRESS = r"ipv6 addr"
    IOS_ISIS_NET = r" net "
    IOS_RID = r"router-id"
    IOS_VRF_RT = r"route-target (ex|im|bo)"
    IOS_VRF_RD = r"rd [1-9]"


    for cfg_line in config:


        if re.search(IOS_BD, cfg_line):
            # Check bridge-domain ID
            if not check_ios_bd(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_BGP_NEIGH_ADDR, cfg_line):
            # Check BGP neighbor IP address, could be IPv4 or IPv6!
            if not check_ios_bgp_neigh_addr(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_INT_DESC, cfg_line):
            # Check interface description format
            if not check_ios_int_desc(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_IPV4_ADDRESS, cfg_line):
            # Check interface IPv4 address and mask
            if not check_ios_int_ipv4(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_IPV4_HELPER, cfg_line):
            # Check interface IPv4 helper address
            if not check_ios_int_ipv4_helper(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_IPV6_ADDRESS, cfg_line):
            # Check interface IPv6 address and mask
            if not check_ios_int_ipv6(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_ISIS_NET, cfg_line):
            # Check ISIS NET
            if not check_ios_isis_net(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_RID, cfg_line):
            # Check router ID e.g. OSPF or BGP, could be IPv4 or IPv6!
            if not check_ios_rid(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_VRF_RD, cfg_line):
            # Check VRF route distinguisher
            if not check_ios_vrf_rd(cfg_line.strip()):
                ret_val = False

        elif re.search(IOS_VRF_RT, cfg_line):
            # Check VRF route target
            if not check_ios_vrf_rt(cfg_line.strip()):
                ret_val = False

    return ret_val


def validate_junos_config(config):

    ret_val = True

    JUNOS_BD_VLAN_ID = r"set bridge-domains .* vlan-id "
    JUNOS_INT_DESC = r"set interfaces .* des"
    JUNOS_INT_VLAN_ID = r"set interfaces [a-z]+(-?)[0-9](/?[0-9]?)+ unit [0-9]+ vlan-id "
    JUNOS_IPV4_ADDRESS = r"set interfaces [a-z]+(-?)[0-9](/?[0-9]?)+ unit [0-9]+ family inet address "
    JUNOS_IPV6_ADDRESS = r"set interfaces [a-z]+(-?)[0-9](/?[0-9]?)+ unit [0-9]+ family inet6 address "


    for cfg_line in config:

        if re.search(JUNOS_BD_VLAN_ID, cfg_line):
            # Check bridge-domain VLAN ID
            if not check_junos_bd_vlan_id(cfg_line.strip()):
                ret_val = False

        elif re.search(JUNOS_INT_DESC, cfg_line):
            # Check interface description format
            if not check_junos_int_desc(cfg_line.strip()):
                ret_val = False

        elif re.search(JUNOS_INT_VLAN_ID, cfg_line):
            # Check VLAN number
            if not check_junos_int_vlan_id(cfg_line.strip()):
                ret_val = False

        elif re.search(JUNOS_IPV4_ADDRESS, cfg_line):
            # Check interface IPv4 address and mask
            if not check_junos_int_ipv4(cfg_line.strip()):
                ret_val = False

        elif re.search(JUNOS_IPV6_ADDRESS, cfg_line):
            # Check interface IPv6 address and mask
            if not check_junos_int_ipv6(cfg_line.strip()):
                ret_val = False


    return ret_val


def main():
    
    args = parse_cli_args()

    cfg_filename = args['config_file']
    
    check_file_exists(cfg_filename)

    print("Syntax checking: {}".format(cfg_filename))


    config = []

    try:
        cfg_file = open(cfg_filename)
    except Exception as e:
        print("Couldn't open config file {}: {}".format(cfg_filename, e))
        sys.exit(1)

    try:
        config = cfg_file.readlines()
    except Exception as e:
        print("Couldn't load config file {}: {}".format(cfg_filename, e))
        cfg_file.close()
        sys.exit(1)

    cfg_file.close()

    if args['type'] == "ios":
        if validate_ios_config(config):
            print("Config passed without issue")
        else:
            print("Config file failed checks")
            sys.exit(1)

    elif args['type'] == 'junos':
        if validate_junos_config(config):
            print("Config passed without issue")
        else:
            print("Config file failed checks")
            sys.exit(1)

    else:
        print("Unsupported device type: {}".format(args['type']))
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
