import requests
import json
import paramiko
from datetime import datetime
import logging
import urllib3

# ScienceLogic Specific Imports
# import sl_snippets as em7_snippets
from silo.apps.sl1_data_model import get_cred_array_from_id
from silo.apps.storage import dbc_cursor


# Disable insecure warnings for internal GQL calls
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

# File Paths
files = {
    "hostname_class": local_remote_path + 'hostname_class.yml',
    "ip_class": local_remote_path + 'ipaddress_class.yml',
    "id_class": local_remote_path + 'deviceid_class.yml',
    "host_ip": local_remote_path + 'hostname_ipaddress.yml',
    "ip_host": local_remote_path + 'ipaddress_hostname.yml',
    "deviceid_host": local_remote_path + 'deviceid_host.yml',
    "deviceid_ip": local_remote_path + 'deviceid_ip.yml'
}

# --- Database and Credential Retrieval ---

# Initialize the ScienceLogic DBC Cursor
dbc = dbc_cursor(legacy=True)

# Fetch ScienceLogic API Credentials
# Ensure sl_api_cred_id is defined in your environment
sl_cred = get_cred_array_from_id(dbc, int(sl_api_cred_id))
sl_url = sl_cred.get("curl_url", "").rstrip('/')
sl_gql_url = f"{sl_url}/gql"
sl_user_name = sl_cred.get("cred_user")
sl_password = sl_cred.get("cred_pwd")

# Fetch ELK SSH Credentials
# Ensure elk_cred_id and hostnames list are defined
hostnames = ["192.168.2.167", "192.168.2.168", "192.168.2.169"]
elk_cred = get_cred_array_from_id(dbc, int(elk_cred_id))
elk_username = elk_cred.get("cred_user")
elk_password = elk_cred.get("cred_pwd")

def fetch_all_devices_gql():
    """
    Uses GraphQL to fetch all devices using pagination.
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

    logger.info("Starting GraphQL extraction using dbc_cursor credentials...")

    while has_next_page:
        variables = {"first": 500, "after": cursor}
        try:
            response = requests.post(
                sl_gql_url, 
                json={'query': gql_query, 'variables': variables}, 
                auth=auth, 
                verify=False,
                timeout=60
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
                logger.info(f"Batch {batch_count}: Progress {len(all_devices)}/{total_matches}")
            
            batch_count += 1
            
        except Exception as e:
            logger.error(f"GQL Error on batch {batch_count}: {str(e)}")
            break

    return all_devices

def process_and_write_files(devices):
    """
    Generates 7 YML files in the required key-value format.
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
                raw_id = node['id']
                dev_id = raw_id.split("/")[-1] if "/" in raw_id else raw_id
                hostname = node['name'].split(":")[0].lower()
                ip = node['ip']
                dev_class_desc = node.get('deviceClass', {}).get('description', 'Unknown')

                # Maintain exact formatting for ELK ingestion
                f_h_class.write(f'"{hostname}": "{dev_class_desc}"\n')
                f_i_class.write(f'"{ip}": "{dev_class_desc}"\n')
                f_id_class.write(f'"{dev_id}": "{dev_class_desc}"\n')
                
                f_id_h.write(f'"{hostname}": "{dev_id}"\n')
                f_id_i.write(f'"{ip}": "{dev_id}"\n')

                if hostname and ip:
                    f_h_ip.write(f'"{hostname}": "{ip}"\n')
                    f_i_h.write(f'"{ip}": "{hostname}"\n')

        logger.info("YAML files generated successfully.")
    except Exception as e:
        logger.error(f"File writing error: {str(e)}")

def create_sftp_client(host, user, pwd):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username=user, password=pwd)
        return ssh, ssh.open_sftp()
    except Exception as e:
        logger.error(f"SFTP Connection failed for {host}: {str(e)}")
        return None, None

# --- Main Execution ---

device_list = fetch_all_devices_gql()

if device_list:
    process_and_write_files(device_list)

    file_paths = list(files.values())
    for target_host in hostnames:
        ssh, sftp = create_sftp_client(target_host, elk_username, elk_password)
        if sftp:
            try:
                # NEW: Ensure remote directory exists
                try:
                    sftp.chdir(remote_path_file)  # Try to enter the directory
                except IOError:
                    logger.warning(f"Remote path {remote_path_file} not found on {target_host}. Attempting to create.")
                    # This creates the directory if permissions allow
                    ssh.exec_command(f'mkdir -p {remote_path_file}')
                
                for path in file_paths:
                    fname = path.split('/')[-1]
                    remote_destination = remote_path_file + fname
                    sftp.put(path, remote_destination)
                    logger.info(f"Successfully transferred {fname} to {target_host}")
                    
            except Exception as e:
                logger.error(f"Transfer error on {target_host}: {str(e)}")
            finally:
                sftp.close()
                ssh.close()
        else:
            logger.error(f"Skipping {target_host} due to connection failure.")