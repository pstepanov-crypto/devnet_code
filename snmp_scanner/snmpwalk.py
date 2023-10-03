from easysnmp import Session , EasySNMPError
import getopt
import sys
import ipaddress
import csv  # Import the csv module

 SNMP_COMMUNITY = "public"

def scanNet(ip):
    global SNMP_COMMUNITY
     session = Session(hostname=ip, community=SNMP_COMMUNITY, version=2, timeout = 0.01)  # Use SNMP

    try:

        model = session.get(".1.3.6.1.2.1.47.1.1.1.1.13.2000").value
        hostname = session.get(".1.3.6.1.2.1.1.5.0").value
        serial_number = session.get(".1.3.6.1.2.1.47.1.1.1.1.11.1000").value  # Cisco WS-C6509-E

         if serial_number.endswith("STANCE"):
            serial_number = session.get(".1.3.6.1.2.1.47.1.1.1.1.11.1001").value  # cisco 2960
        if serial_number.endswith("STANCE"):
            serial_number = session.get(".1.3.6.1.2.1.47.1.1.1.1.11.1").value  # Cisco WS-C6509-E
        if serial_number.endswith("STANCE"):
            serial_number = session.get(".1.3.6.1.2.1.47.1.1.1.1.11.149").value #  Nexus value
        if serial_number.endswith("STANCE"):
            serial_number = session.get(".1.3.6.1.2.1.47.1.1.1.1.11.16842753").value #Huawei value

 

        if model.endswith("UPOE+E"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.13.1").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.2.149").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.7.1").value # 3850   
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.2.1000").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.13.149").value
        if model.endswith("STANCE"):
            model = session.get("1.3.6.1.2.1.47.1.1.1.1.13.10").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.7.149").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.13.1").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.13.1001").value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.47.1.1.1.1.7.16842753").value #Huawei value
        if model.endswith("STANCE"):
            model = session.get(".1.3.6.1.2.1.25.6.3.1.2.150").value   

         # You can add more conditions here as needed
 
        print(f"Scanning device {hostname} with IP: {ip}, Serial Number: {serial_number}, Model: {model}")

       # before need create scan_results.csv file
       with open("scan_results.csv", mode="r") as file:
        reader = csv.reader(file)
        serial_in_file = [row[0] for row in reader]

       if serial_number not in serial_in_file:
        # Append the data to the CSV file
            with open("scan_results.csv", mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([model, hostname, ip, serial_number])
       else:
            print(f"Hostname {hostname} already in file, skipping.")
   

    except EasySNMPError as e:
        print(f"Error scanning device {ip}: {e}")
        #SNMP_COMMUNITY = "public2"  # Change SNMP_COMMUNITY on SNMP error (this is not working ..)


def main():
    subnet = None

     if len(sys.argv) < 2:
        usage()
        sys.exit()


    try:
        opts, args = getopt.getopt(sys.argv[1:], "s:h", ["help"])
    except getopt.GetoptError as err:
        # Print help information and exit:
        print(str(err))
        usage()
        sys.exit(2)

     for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-s"):
            subnet = a


    if subnet is None:
        usage()
        sys.exit(2)

     # Generate a list of IP addresses within the specified subnet
    try:
        subnet = ipaddress.IPv4Network(subnet)
        ip_addresses = [str(ip) for ip in subnet.hosts()]
    except ValueError as e:
        print(f"Invalid subnet: {e}")
        sys.exit(2)

 
    # Iterate through the IP addresses and perform SNMP queries
    for ip_address in ip_addresses:
        scanNet(ip_address)


def usage():
    print("\nNetwork discovery tool. Options:")
    print("-s Subnet [Subnet to scan, e.g., 192.168.1.0/24]")

 
if __name__ == "__main__":
    main()
