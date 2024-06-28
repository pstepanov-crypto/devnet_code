import requests
from netmiko import ConnectHandler
import ipaddress
import re
import yaml
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor

# Define the network ranges
network_ranges = ['192.168.0.0/24', '192.168.1.0/24']

# Define the device parameters Pattern not detected
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# NetBox API configuration
netbox_url = 'http://172.16.125.6/api/'  # Replace with your NetBox URL
netbox_token = 'c0eeb3883609915b8c13a3c0a1292406878e8eec'  # Replace with your NetBox API token
headers = {
    'Authorization': f'Token {netbox_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Function to fetch NetBox object ID by name
def get_netbox_id(endpoint, name):
    response = requests.get(f'{netbox_url}{endpoint}', headers=headers, params={'name': name})
    if response.status_code == 200 and response.json()['count'] > 0:
        return response.json()['results'][0]['id']
    else:
        print(f"Failed to get ID for {name} from {endpoint}")
        return None

# Function to fetch NetBox device type ID by PID
def get_device_type_id_by_pid(pid):
    response = requests.get(f'{netbox_url}dcim/device-types/', headers=headers, params={'part_number': pid})
    if response.status_code == 200 and response.json()['count'] > 0:
        return response.json()['results'][0]['id']
    else:
        print(f"Failed to get device type ID for PID {pid}")
        return None

# Static IDs based on your example
device_role_id = 46

# Function to determine site_id based on network range
def determine_site_id(network_range):
    if network_range == '192.168.0.0/24':
        return 30
    elif network_range == '192.168.1.0/24':
        return 31
    else:
        print("Unknown network range.")
        return None

# Function to add a device to NetBox
def add_device_to_netbox(hostname, pid, sn, site_id):
    # Determine the device_type_id based on pid
    device_type_id = get_device_type_id_by_pid(pid)
    if not device_type_id:
        print(f"Unknown device type for PID {pid}, skipping.")
        return

    # Create the device data
    device_data = {
        'name': hostname,
        'serial': sn,
        'device_type': device_type_id,
        'role': device_role_id,
        'device_role': device_role_id,
        'site': site_id,
        'status': 'active',  # Set the status to active
    }

    # Check if the device already exists in NetBox by serial number
    response = requests.get(f'{netbox_url}dcim/devices/', headers=headers, params={'serial': sn})
    if response.status_code == 200 and len(response.json()['results']) > 0:
        print(f"Device with serial {sn} already exists in NetBox, skipping.")
        return

    # Add the device to NetBox
    response = requests.post(f'{netbox_url}dcim/devices/', headers=headers, json=device_data)
    if response.status_code == 201:
        print(f"Device {hostname} added to NetBox.")
    else:
        print(f"Failed to add device {hostname} to NetBox: {response.status_code} - {response.text}")

# Loop through each network range
with ThreadPoolExecutor(max_workers=2) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Determine site_id for the current network range
        site_id = determine_site_id(network_range)

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)

                # Send the command to get inventory information
                output = net_connect.send_command('show inventory')

                # Regular expression to extract device information
                match = re.search(r'PID:\s*(\S+)\s*,.*SN:\s*(\S+)', output)
                if match:
                    pid = match.group(1)
                    sn = match.group(2)

                    # Determine the hostname
                    hostname = device_params['ip']

                    # Add the device to NetBox
                    add_device_to_netbox(hostname, pid, sn, site_id)

                # Disconnect from the device
                net_connect.disconnect()

            except SSHException as e:
                print(f"SSH Connection Error: {e}")

            except Exception as ex:
                print(f"An error occurred: {ex}")
