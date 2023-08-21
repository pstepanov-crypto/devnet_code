# add prefixes through ansible to netbox
import csv
import yaml

excel_filename = "tst.csv"
yaml_filename = excel_filename.replace('csv', 'yaml')

common_name = "generate prefix"
netbox = ""
url = '"netbox ip address"'
token = "apy key netbox"
data = ""
state = "present"

users = []

with open(excel_filename, "r") as excel_csv:
    csv_reader = csv.reader(excel_csv)
    for line in csv_reader:
        if len(line) == 4:
            opis, prefix, descr, coma = [item.strip() for item in line]
            full_prefix = f"{prefix}/{descr}"
              
            user_data = {
                '- name': common_name,
                '  netbox.netbox.netbox_prefix': netbox,
                '    netbox_url': url,
                '    netbox_token': token,
                '    data': f"\n          prefix: {full_prefix}\n          description: {opis}\n          comments: {coma}\n        state: {state}\n"
            }
            users.append(user_data)



with open(yaml_filename, "w+") as yf:
    yf.write("  tasks:\n")
    for user in users:
        for k, v in user.items():
            yf.write(f"    {k}: {v}\n")
