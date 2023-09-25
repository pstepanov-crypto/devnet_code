import csv
from pynetbox import api

# Define your NetBox API URL and authentication credentials
NB_URL = "netbox ip address"
API_TOKEN = "token"

# Initialize the NetBox API client
netbox = api(url=NB_URL, token=API_TOKEN)

try:
    # Retrieve all IP prefixes from NetBox
    prefixes = netbox.ipam.prefixes.all()

    if prefixes:
        # Create a list to hold the data to be saved in the CSV file
        data_to_save = [["Prefix", "Description", "VRF", "Tenant"]]

        # Iterate through the prefixes and add relevant data to the list
        for prefix in prefixes:
            data_to_save.append([prefix.prefix, prefix.description, prefix.vrf.name, prefix.tenant.name])

        # Specify the CSV file path where you want to save the data
        csv_file_path = "output.csv"

        # Write the data to the CSV file
        with open(csv_file_path, "w", newline="") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerows(data_to_save)

        print(f"Data saved to {csv_file_path}")
    else:
        print("No IP prefixes found in NetBox.")
except Exception as e:
    print(f"Error: {e}")
