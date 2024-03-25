from netmiko import ConnectHandler
import ipaddress
import re
import csv
import yaml
from paramiko.ssh_exception import SSHException
from itertools import repeat
from concurrent.futures import ThreadPoolExecutor

# Define the network ranges
network_ranges = ['192.168.0.0/24', '192.168.1.0/24']



# Define the device parameters
with open('device_params.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

#Threads is not work for multiple network ranges
#with ThreadPoolExecutor(max_workers=5) as executor:
for network_range in network_ranges:
    network = ipaddress.ip_network(network_range)

    # Loop through each IP address in the network range

    for ip in network:
        device_params['ip'] = str(ip)
        try:
            # Connect to the device
            net_connect = ConnectHandler(**device_params)

            # Show command to identify existing IP access-list standard vty on device
            sh_output = net_connect.send_command('show ip access-lists vty')

            if 'Standard IP access list vty' in sh_output:
                output = net_connect.send_config_set(['ip access-list standard vty', 'permit 10.7.255.20', 'end', 'wr'])
                
            # Determine the hostname
            hostname = device_params['ip']

            print(f"Command is committed for {hostname}")
            #print(sh_output)

            # Disconnect from the device
            net_connect.disconnect()
            
        #For nexus i use try - except
        except '\\ terminal\\ length\\ 0' as x:
            device_type = 'cisco_nxos'
            output = net_connect.send_config_set(['ip access-list vty', 'permit ip 10.7.255.26/32 any', 'end', 'copy run startup-config'])
            print(f"SSH Connection Error: {x}")

        except SSHException as e:
            print(f"SSH Connection Error: {e}")

        except Exception as ex:
            print(f"An error occurred: {ex}")
