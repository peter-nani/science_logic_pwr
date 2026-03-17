import json
import os

# 1. The Mock Data from your GraphQL response
mock_gql_response = {
    "data": {
        "devices": {
            "pageInfo": {
                "hasNextPage": True,
                "matchCount": 394,
                "__typename": "PageInfo"
            },
            "edges": [
                {
                    "cursor": "eyJjIjozOTQsImlkIjoiMSIsImlkeCI6MCwic2VhcmNoQW5kU29ydEhhc2giOiJpdEs4ZW5IZDE3MEtBL2xKRlhiYTljU3lJQWpXc2ppMnRlSldQUXBFYkFVPSJ9",
                    "node": {
                        "name": "sgpl-lab3216",
                        "ip": "192.168.4.216",
                        "id": "1",
                        "deviceClass": {
                            "class": "Linux",
                            "description": "Red Hat Enterprise Linux 7"
                        }
                    }
                }
            ]
        }
    }
}

# 2. Local File Definitions (Setting paths to Current Working Directory)
cwd = os.getcwd()
files = {
    "hostname_class": os.path.join(cwd, 'hostname_class.yml'),
    "ip_class": os.path.join(cwd, 'ipaddress_class.yml'),
    "id_class": os.path.join(cwd, 'deviceid_class.yml'),
    "host_ip": os.path.join(cwd, 'hostname_ipaddress.yml'),
    "ip_host": os.path.join(cwd, 'ipaddress_hostname.yml'),
    "deviceid_host": os.path.join(cwd, 'deviceid_host.yml'),
    "deviceid_ip": os.path.join(cwd, 'deviceid_ip.yml')
}

def process_and_write_files_VERIFY(devices):
    """
    Extracted logic from your main script to verify YAML formatting.
    """
    try:
        with open(files["hostname_class"], 'w+') as f_h_class, \
             open(files["ip_class"], 'w+') as f_i_class, \
             open(files["id_class"], 'w+') as f_id_class, \
             open(files["host_ip"], 'w+') as f_h_ip, \
             open(files["ip_host"], 'w+') as f_i_h, \
             open(files["deviceid_host"], 'w+') as f_id_h, \
             open(files["deviceid_ip"], 'w+') as f_id_i:

            for node in devices:
                # --- START OF LOGIC ALIGNMENT ---
                raw_id = node['id']
                dev_id = raw_id.split("/")[-1] if "/" in raw_id else raw_id
                
                # Handling hostname: split by colon (if any) and lowercase
                hostname = node['name'].split(":")[0].lower()
                ip = node['ip']
                
                # Fetching description from the nested deviceClass object
                dev_class_desc = node.get('deviceClass', {}).get('description', 'Unknown')

                # Writing exactly as the production script would
                f_h_class.write(f'"{hostname}": "{dev_class_desc}"\n')
                f_i_class.write(f'"{ip}": "{dev_class_desc}"\n')
                f_id_class.write(f'"{dev_id}": "{dev_class_desc}"\n')
                
                # Cross-reference files
                f_id_h.write(f'"{hostname}": "{dev_id}"\n')
                f_id_i.write(f'"{ip}": "{dev_id}"\n')

                if hostname and ip:
                    f_h_ip.write(f'"{hostname}": "{ip}"\n')
                    f_i_h.write(f'"{ip}": "{hostname}"\n')
                # --- END OF LOGIC ALIGNMENT ---

        print(f"Success! 7 files created in: {cwd}")
    except Exception as e:
        print(f"Error writing files: {e}")

# --- Run the Verification ---

# Extract nodes from the mock response
extracted_nodes = [edge['node'] for edge in mock_gql_response['data']['devices']['edges']]

# Generate the files
process_and_write_files_VERIFY(extracted_nodes)