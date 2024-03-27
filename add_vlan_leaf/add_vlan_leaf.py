from netmiko import ConnectHandler, NetMikoTimeoutException
import ipaddress
import re
import csv
import yaml
from paramiko.ssh_exception import SSHException
from itertools import repeat
from concurrent.futures import ThreadPoolExecutor

#Try to use address range for future
#[ipaddr for ipaddr in ipaddress.summarize_address_range(ipaddress.IPv4Address('10.6.250.21'),ipaddress.IPv4Address('10.6.250.34'))]


# Define the network ranges
network_ranges = ['192.168.0.1/32', '192.168.0.2/32']

# Define the device parameters
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Threads for multiple network ranges
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)

                output = net_connect.send_config_set(['vlan 100',
                                                      'name test',
                                                      'interface Vlan100',
                                                      'description test',
                                                      'no shutdown',
                                                      'mtu 9216',
                                                      'vrf member test',
                                                      'no ip redirects',
                                                      'ip address 192.168.0.1/27',
                                                      'no ipv6 redirects',
                                                      'fabric forwarding mode anycast-gateway',
                                                      'end',
                                                      'copy run startup-config'])
                
                # Determine the hostname
                hostname = device_params['ip']
                print(f"Command is committed for {hostname}")

                # Disconnect from the device
                net_connect.disconnect()
                               
            except SSHException as e:
                print(f"SSH Connection Error: {e}")
                
            except Exception as ex:
                print(f"An error occurred: {ex}")
