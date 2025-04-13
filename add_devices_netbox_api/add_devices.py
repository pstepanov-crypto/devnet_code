#Скрипт сканирует подсети '192.168.0.0/24', '192.168.1.0/24' итд. и добавляет сетевые устройства в Netbox через ssh на основе регулярного выражения из команды sh inventory
#так же добавляет устройства и в стеках
import requests
import certifi
from netmiko import ConnectHandler
import ipaddress
import re
import yaml
from paramiko.ssh_exception import SSHException
from concurrent.futures import ThreadPoolExecutor



# Define the network ranges
network_ranges = ['192.168.0.0/24']

# Define the device parameters
with open('device_params_nxos.yaml') as file:
    device_params = yaml.load(file, Loader=yaml.FullLoader)

# NetBox API configuration
netbox_url = ''  # Replace with your NetBox URL
netbox_token = ''  # Replace with your NetBox API token
headers = {
    'Authorization': f'Token {netbox_token}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

# Function to fetch NetBox object ID by name
def get_netbox_id(endpoint, name):
    response = requests.get(f'{netbox_url}{endpoint}', headers=headers, params={'name': name}, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 200 and response.json()['count'] > 0:
        return response.json()['results'][0]['id']
    else:
        print(f"Failed to get ID for {name} from {endpoint}")
        return None

# Function to fetch NetBox device type ID by PID
def get_device_type_id_by_pid(pid):
    response = requests.get(f'{netbox_url}dcim/device-types/', headers=headers, params={'part_number': pid}, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 200 and response.json()['count'] > 0:
        return response.json()['results'][0]['id']
    else:
        print(f"Failed to get device type ID for PID {pid}")
        return None

# Function to check if hostname exists in NetBox
def check_hostname_exists(hostname):
    response = requests.get(f'{netbox_url}dcim/devices/', headers=headers, params={'name': hostname}, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 200 and response.json()['count'] > 0:
        return True
    return False

# Static IDs based on your example
device_role_id = 46
site = 45
site_deactivated = 38

# Function to add a device to NetBox
def add_device_to_netbox(hostname, pid, sn, site_id, ip_address):
    # Determine the device_type_id based on pid
    device_type_id = get_device_type_id_by_pid(pid)
    if not device_type_id:
        print(f"Unknown device type for PID {pid}, skipping.")
        return None

    original_hostname = hostname  # Save the original hostname for suffix generation
    suffix_count = 1

    # Ensure the hostname is unique
    while check_hostname_exists(hostname):
        # Modify the hostname with a stack suffix if it already exists
        hostname = f"{original_hostname}_stack{suffix_count}"
        suffix_count += 1

    # Create the device data
    device_data = {
        'name': hostname,
        'serial': sn,
        'device_type': device_type_id,
        'device_role': device_role_id,
        'role': device_role_id,
        'site': site_id,
        'status': 'active',  # Set the status to active
        'custom_fields': {
            'scanned_ip': ip_address
        }
    }

    # Check if the device already exists in NetBox by serial number
    response = requests.get(f'{netbox_url}dcim/devices/', headers=headers, params={'serial': sn}, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 200 and len(response.json()['results']) > 0:
        print(f"Device with serial {sn} already exists in NetBox, skipping.")
        return response.json()['results'][0]['id']

    # Add the device to NetBox
    response = requests.post(f'{netbox_url}dcim/devices/', headers=headers, json=device_data, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 201:
        print(f"Device {hostname} added to NetBox.")
        return response.json()['id']
    else:
        print(f"Failed to add device {hostname} to NetBox: {response.status_code} - {response.text}")
        return None

# Function to get current inventory items for a device in NetBox
def get_current_inventory(device_id):
    response = requests.get(f'{netbox_url}dcim/inventory-items/', headers=headers, params={'device_id': device_id}, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 200:
       return response.json()['results']
    else:
        print(f"Failed to get current inventory for device {device_id}: {response.status_code} - {response.text}")
        return []

# Function to add inventory item to a device in NetBox
def add_inventory_item_to_device(device_id, part_id, serial, name):
    # Check if the inventory item already exists in NetBox by serial number
    response = requests.get(f'{netbox_url}dcim/inventory-items/', headers=headers, params={'serial': serial}, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 200 and len(response.json()['results']) > 0:
        print(f"Inventory item with serial {serial} already exists in NetBox, skipping.")
        return response.json()['results'][0]['id']
    
    inventory_data = {
        'device': device_id,
        'name': name,
        'part_id': part_id,
        'serial': serial,
    }

    response = requests.post(f'{netbox_url}dcim/inventory-items/', headers=headers, json=inventory_data, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 201:
        print(f"Inventory item {name} added to NetBox.")
        return response.json()['id']
    else:
        print(f"Failed to add inventory item {name} to NetBox: {response.status_code} - {response.text}")

# Function to remove inventory item from a device in NetBox
def remove_inventory_item(item_id):
    response = requests.delete(f'{netbox_url}dcim/inventory-items/{item_id}/', headers=headers, verify='/root/project/netbox_add_final/netbox.pem')
    if response.status_code == 204:
        print(f"Inventory item {item_id} removed from NetBox.")
    else:
        print(f"Failed to remove inventory item {item_id} from NetBox: {response.status_code} - {response.text}")

# Loop through each network range
with ThreadPoolExecutor(max_workers=2) as executor:
    for network_range in network_ranges:
        network = ipaddress.ip_network(network_range)

        # Determine site_id for the current network range
        site_id = site

        # Loop through each IP address in the network range
        for ip in network:
            device_params['ip'] = str(ip)
            device_id = None  # Initialize device_id before the try block
            try:
                # Connect to the device
                net_connect = ConnectHandler(**device_params)

                # Send the command to get inventory information
                output = net_connect.send_command('show inventory')
                output3 = net_connect.send_command('show ver')
                
                # Regular expression to extract SFP, GLC, QSFP, SFBR, CVR, Unspecified information - dell regex
                regex = r'NAME: ".*?", DESCR: ".*?"\s+PID:\s*(SFP-\S+|GLC-\S+|QSFP-\S+|SFBR-\S+|CVR-\S+|X2-\S+|Unspecified-\S+)\s*,\s*VID:\s*\S*\s*,\s*SN:\s*(\S+)'
                matches = re.findall(regex, output)

                # Regular expression to extract device PID and SN
                match2 = re.findall(r'PID:\s*(\S+)\s*,.*SN:\s*(\S+)', output)
                match3 = re.findall(r"(.*?)\s+uptime", output3)
                match4 = re.findall(r"Device name: (.+)", output3)
                
                # Determine the hostname
                hostname = match3[0] if match3 else ""
                if 'kernel' in hostname.lower():
                    hostname = match4[0] if match4 else hostname
                
                # Add the device to NetBox
                if match2:
                    for match in match2:
                        pid = match[0]
                        sn = match[1]
                        device_id = add_device_to_netbox(hostname, pid, sn, site_id, str(ip))

                # Get the current inventory items from NetBox
                current_inventory = get_current_inventory(device_id) if device_id else []

                # Extract the current inventory SFP serials
                current_inventory_serials = {item['serial']: item['id'] for item in current_inventory}

               # Add inventory items to the device if any matches were found
                new_inventory_serials = set()
                if matches and device_id:
                    for sfp_info in matches:
                        sfp_pid = sfp_info[0]
                        sfp_sn = sfp_info[1].strip()
                        new_inventory_serials.add(sfp_sn)

                        if sfp_sn not in current_inventory_serials:
                            add_inventory_item_to_device(device_id, sfp_pid, sfp_sn, sfp_pid)

                # Remove inventory items that are no longer present
                for serial, item_id in current_inventory_serials.items():
                    if serial not in new_inventory_serials:
                        remove_inventory_item(item_id)

                # Disconnect from the device
                net_connect.disconnect()

            except SSHException as e:
                print(f"SSH Connection Error: {e}")
                # Handle connection errors as needed

            except Exception as ex:
                print(f"An error occurred: {ex}")
