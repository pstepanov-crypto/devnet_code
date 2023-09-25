import csv
from pynetbox import api
from smbprotocol.open import open_file
from smbprotocol.session import Session
from smbprotocol.tree import TreeConnect

# Define your NetBox API URL and authentication credentials
NB_URL = "http://172.16.125.6"
API_TOKEN = "token"

# Initialize the NetBox API client
netbox = api(url=NB_URL, token=API_TOKEN)

# Define remote machine credentials and share details
remote_machine = "remote-machine"
share_name = "share-folder"
username = "your-username"
password = "your-password"
domain = "your-domain"

try:
    # Retrieve all IP prefixes from NetBox
    prefixes = netbox.ipam.prefixes.all()

    if prefixes:
        # Create a list to hold the data to be saved in the CSV file
        data_to_save = [["Prefix", "Description", "VRF", "Tenant"]]

        # Iterate through the prefixes and add relevant data to the list
        for prefix in prefixes:
            data_to_save.append([prefix.prefix, prefix.description, prefix.vrf, prefix.tenant])

        # Specify the local CSV file path
        local_csv_file_path = "output.csv"

        # Write the data to the local CSV file
        with open(local_csv_file_path, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(data_to_save)

        # Create an SMB session to the remote machine
        session = Session()
        session.login(f"\\\\{remote_machine}", username, password, domain)

        # Connect to the remote share
        with TreeConnect(session, share_name) as tree:
            # Upload the local CSV file to the remote share
            with open_file(tree, "output.csv", "w") as remote_file:
                with open(local_csv_file_path, "rb") as local_file:
                    remote_file.write(local_file.read())

        print(f"Data saved to {local_csv_file_path} and uploaded to remote share.")
    else:
        print("No IP prefixes found in NetBox.")
except Exception as e:
    print(f"Error: {e}")
