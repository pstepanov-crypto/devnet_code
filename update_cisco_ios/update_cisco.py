from netmiko import ConnectHandler, NetMikoTimeoutException
import ipaddress
import yaml
import time
from paramiko.ssh_exception import SSHException
from jinja2 import Environment, FileSystemLoaderghb
from concurrent.futures import ThreadPoolExecutor


# List of update
network_ranges = [ '192.168.0.1/32', '192.168.0.2/32']


# Define the device parameters
with open('device_params.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Iterate over network ranges
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)
                
                # Send command
                command = "copy tftp://192.168.0.1/c2960x-universalk9-mz.152-7.E9.bin flash:c2960x-universalk9-mz.152-7.E9.bin"
                output = net_connect.send_command(command, expect_string='\w')
                output += net_connect.send_command('\n', expect_string='\w')

                # Determine the hostname
                hostname = device_params['ip']
                print(f"Configuration sent successfully to {ip}")
                #print(output)

                # Disconnect from the device after 16 min
                time.sleep(1000)
                net_connect.disconnect()

            except SSHException as e:
                print(f"SSH Connection Error: {e}")

            except Exception as ex:
                print(f"An error occurred: {ex}")
