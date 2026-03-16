import requests
import json
import paramiko
from datetime import datetime
import logging
from silo_common.credentials import cred_array_from_id
from silo_common.database import local_db
import silo_common.snippets as em7_snippets

# Set up logging
log_file_name = '/data/logs/sl_elk/api_fetch.log'
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_formatter = logging.Formatter('%(asctime)s,%(levelname)s,%(lineno)d,%(message)s')
log_file_handler = logging.FileHandler(log_file_name)
log_file_handler.setFormatter(log_formatter)
logger.addHandler(log_file_handler)

# Configuration
local_remote_path = "/data/logs/sl_elk/"
remote_path_file = "/opt/elk/logstash/config/enrichment_sl/"

# File Paths (Kept exactly as requested)
files = {
    "hostname_class": local_remote_path + 'hostname_class.yml',
    "ip_class": local_remote_path + 'ipaddress_class.yml',
    "id_class": local_remote_path + 'deviceid_class.yml',
    "host_ip": local_remote_path + 'hostname_ipaddress.yml',
    "ip_host": local_remote_path + 'ipaddress_hostname.yml',
    "deviceid_host": local_remote_path + 'deviceid_host.yml',
    "deviceid_ip": local_remote_path + 'deviceid_ip.yml'
}

# Credentials (Assumes variables sl_api_cred_id, elk_cred_id, and hostnames are provided in environment)
sl_api_cred_details = cred_array_from_id(local_db())(int(sl_api_cred_id))
sl_gql_url = sl_api_cred_details['curl_url'].replace('/api', '/gql') # Adjusting URL for GQL endpoint
sl_user_name = sl_api_cred_details['cred_user']
sl_password = sl_api_cred_details['cred_pwd']

ssh_cred_details = cred_array_from_id(local_db())(int(elk_cred_id))
elk_username = ssh_cred_details['cred_user']
elk_password = ssh_cred_details['cred_pwd']

def fetch_all_devices_gql():
    """
    Uses GraphQL to fetch all devices using pagination.
    Returns a list of all device nodes.
    """
    all_devices = []
    has_next_page = True
    cursor = ""
    batch_count = 1
    auth = (sl_user_name, sl_password)

    gql_query = """
    query GetDevices($first: Int, $after: String) {
      devices(first: $first, after: $after) {
        pageInfo {
          hasNextPage
          matchCount
        }
        edges {
          cursor
          node {
            id
            name
            ip
            deviceClass {
              class
              description
            }
          }
        }
      }
    }
    """

    logger.info("Starting GraphQL data extraction...")

    while has_next_page:
        variables = {"first": 500, "after": cursor}
        try:
            response = requests.post(
                sl_gql_url, 
                json={'query': gql_query, 'variables': variables}, 
                auth=auth, 
                verify=False
            )
            response.raise_for_status()
            data = response.json()
            
            device_data = data['data']['devices']
            edges = device_data['edges']
            
            for edge in edges:
                all_devices.append(edge['node'])
            
            has_next_page = device_data['pageInfo']['hasNextPage']
            total_matches = device_data['pageInfo']['matchCount']
            
            if edges:
                cursor = edges[-1]['cursor']
                logger.info(f"Batch {batch_count}: Fetched {len(edges)} records. Total progress: {len(all_devices)}/{total_matches}")
            
            batch_count += 1
            
        except Exception as e:
            logger.error(f"GraphQL request failed on batch {batch_count}: {str(e)}")
            break

    logger.info(f"Extraction complete. Total devices retrieved: {len(all_devices)}")
    return all_devices

def process_and_write_files(devices):
    """
    Processes the GQL list and writes the 7 required YML files.
    """
    try:
        # Open all handles
        with open(files["hostname_class"], 'w+') as f_h_class, \
             open(files["ip_class"], 'w+') as f_i_class, \
             open(files["id_class"], 'w+') as f_id_class, \
             open(files["host_ip"], 'w+') as f_h_ip, \
             open(files["ip_host"], 'w+') as f_i_h, \
             open(files["deviceid_host"], 'w+') as f_id_h, \
             open(files["deviceid_ip"], 'w+') as f_id_i:

            for node in devices:
                # Standardize data
                raw_id = node['id']
                dev_id = raw_id.split("/")[-1] if "/" in raw_id else raw_id
                hostname = node['name'].split(":")[0].lower()
                ip = node['ip']
                # Default description if deviceClass is missing
                dev_class_desc = node.get('deviceClass', {}).get('description', 'Unknown')

                # Write logic - keeping format exact to previous script
                f_h_class.write(f'"{hostname}": "{dev_class_desc}"\n')
                f_i_class.write(f'"{ip}": "{dev_class_desc}"\n')
                f_id_class.write(f'"{dev_id}": "{dev_class_desc}"\n')
                
                f_id_h.write(f'"{hostname}": "{dev_id}"\n')
                f_id_i.write(f'"{ip}": "{dev_id}"\n')

                if hostname and ip:
                    f_h_ip.write(f'"{hostname}": "{ip}"\n')
                    f_i_h.write(f'"{ip}": "{hostname}"\n')

        logger.info("All YAML enrichment files written successfully.")
    except Exception as e:
        logger.error(f"Failed to write YAML files: {str(e)}")

def create_sftp_client(hostname, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password)
        sftp = ssh.open_sftp()
        return ssh, sftp
    except Exception as e:
        logger.error(f"Failed to create SFTP client for {hostname}: {str(e)}")
        return None, None

# --- Main Execution Flow ---

# 1. Fetch
all_device_nodes = fetch_all_devices_gql()

# 2. Process & Save Locally
if all_device_nodes:
    process_and_write_files(all_device_nodes)

    # 3. Transfer
    file_list = list(files.values())
    for host in hostnames:
        ssh, sftp = create_sftp_client(host, elk_username, elk_password)
        if sftp:
            try:
                for file_path in file_list:
                    file_name = file_path.split('/')[-1]
                    sftp.put(file_path, remote_path_file + file_name)
                    logger.info(f"Transferred {file_name} to {host}")
            except Exception as e:
                logger.error(f"Transfer error on {host}: {str(e)}")
            finally:
                sftp.close()
                ssh.close()
        else:
            logger.error(f"Failed to create SFTP client for {host}")