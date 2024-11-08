from netmiko import ConnectHandler
import ipaddress
import re
import csv
import yaml
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor

# Define the network ranges
network_ranges = ['192.168.0.1/32', '192.168.0.2/32']

# Define the device parameters
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# Loop through each network range
with ThreadPoolExecutor(max_workers=5) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)

                # Disable paging (turn off "press space for more" prompts)
                #net_connect.send_command("terminal length 0")

                # Send the command to get MAC address information
                output = net_connect.send_command('show mac address-table')

                
                # Determine the hostname
                hostname = device_params['ip']

                # Updated regular expression to extract MAC address and interface from lines starting with '*'
                pattern = r'\*\s+\d+\s+(\d{4}\.\w{4}\.\w{4})\s+\S+\s+\S+\s+\S+\s+\S+\s+(\w+/\d+)'
                matches = re.findall(pattern, output)

                # Debug: print matches to verify if regular expression works
                print(f"Matches found for {hostname}: {matches}")

                # Append each MAC address and interface to the CSV file
                with open("mac.csv", mode="a", newline="") as file:
                    writer = csv.writer(file)
                    if matches:  # Only write if there are matches
                        for mac, interface in matches:
                            writer.writerow([hostname, interface, mac])
                            print(f"Data written to CSV for {hostname}: MAC={mac}, Interface={interface}")
                    else:
                        print(f"No matches found in MAC table output for {hostname}")

                # Disconnect from the device
                net_connect.disconnect()

            except SSHException as e:
                print(f"SSH Connection Error: {e}")

            except Exception as ex:
                print(f"An error occurred: {ex}")
