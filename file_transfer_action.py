# Import all Python modules used
import requests
import json
import base64
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

# Log the current time
current_time = datetime.now().time()
logger.info("Enrichment yml files transfered from SL to ELK at " + str(current_time))

### Central DB connection ### id:1
dbc = em7_snippets.dbc_from_cred_id(db_cred_id)
device_count_query = "SELECT COUNT(ld.ip) FROM master_dev.legend_device ld;"
# Fetching subscribers of DA's
dbc.execute(device_count_query)
device_count = dbc.fetchall()
sl_device_count = device_count[0][0]

# SL API Credentials id:
sl_api_cred_details = cred_array_from_id(local_db())(int(sl_api_cred_id))
#sl_server = "10.150.236.75"
sl_url = sl_api_cred_details['curl_url']
sl_user_name = sl_api_cred_details['cred_user']
sl_password = sl_api_cred_details['cred_pwd']

# ELK SSH Credentials id:
hostnames = #["X.X.X.X", "X.X.X.X"] # List of ELK host IPs or hostnames
ssh_cred_details = cred_array_from_id(local_db())(int(elk_cred_id))
elk_username = ssh_cred_details['cred_user']
elk_password = ssh_cred_details['cred_pwd']

# Local file path
local_remote_path = "/data/logs/sl_elk/"

# Remote file path
remote_path_file = "/opt/elk/logstash/config/enrichment_sl/"

# YML File Names
hostname_class_file = local_remote_path + 'hostname_class.yml'
ip_class_file = local_remote_path + 'ipaddress_class.yml'
id_class_file = local_remote_path + 'deviceid_class.yml'
host_ip_file = local_remote_path + 'hostname_ipaddress.yml'
ip_host_file = local_remote_path + 'ipaddress_hostname.yml'
deviceid_host_file = local_remote_path + 'deviceid_host.yml'
deviceid_ip_file = local_remote_path + 'deviceid_ip.yml'


# Function to fetch data from the API
def fetch_data(url, auth):
    try:
        response = requests.get(url, auth=auth, verify=False)
        response.raise_for_status()  # This ensures any error raises an exception
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error("API request failed: " + str(e))
        return None

# Function to create SFTP client
def create_sftp_client(hostname, username, password):
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password)
        sftp = ssh.open_sftp()
        return ssh, sftp
    except Exception as e:
        logger.error("Failed to create SFTP client for " + hostname + ": " + str(e))
        return None, None

# Function to process device information and class information
def process_device_info_and_class():
    # Define API URLs for data pull
    device_info_url = sl_url + '/api/device?limit=' + str(sl_device_count) + '&extended_fetch=1&order._id=asc'
    device_class_url = sl_url + '/api/device?limit=' + str(sl_device_count) + '&link_disp_field=class_type%2Fclass&order._id=asc'
    auth = (sl_user_name, sl_password)

    # Fetch and process device information
    devices_info_res = fetch_data(device_info_url, auth)
    # Fetch and process device class information
    devices_class_res = fetch_data(device_class_url, auth)

    # Ensure both API calls were successful
    if devices_info_res and devices_class_res:
        devices_info = devices_info_res['result_set']
        devices_class = devices_class_res['result_set']

        # Define file paths
        hostname_class_file = local_remote_path + 'hostname_class.yml'
        ip_class_file = local_remote_path + 'ipaddress_class.yml'
        id_class_file = local_remote_path + 'deviceid_class.yml'

        # Open the necessary files for writing
        with open(hostname_class_file, 'w+') as host_class, \
             open(ip_class_file, 'w+') as ip_class, \
             open(id_class_file, 'w+') as id_class:

            # Loop through device classes and write to files
            for dev_class in devices_class:
                dev_id_URI = dev_class['URI']
                dev_id = dev_id_URI.split("/")[-1]  # Extract device ID
                dev_class_desc = dev_class['description']

                # Match the device ID with the hostname and IP from devices_info
                if dev_id_URI in devices_info:
                    hostname = devices_info[dev_id_URI]['name'].lower()
                    dev_ip = devices_info[dev_id_URI]['ip']


                    # Write the data to respective files
                    host_class.write('"' + hostname + '": "' + dev_class_desc + '"\n')
                    ip_class.write('"' + dev_ip + '": "' + dev_class_desc + '"\n')
                    id_class.write('"' + dev_id + '": "' + dev_class_desc + '"\n')

        #logger.info("Files written successfully.")

# Call the function to process the device info and class
process_device_info_and_class()

def fetch_process_and_transfer_device_data():
    # Define the API URL and authentication
    device_info_url = sl_url + '/api/device?limit=' + str(sl_device_count) + '&extended_fetch=1&link_disp_field=name'
    auth = (sl_user_name, sl_password)

    # Fetch data from the API
    response = requests.get(device_info_url, auth=auth, verify=False)

    # Check if the API call was successful
    if response.status_code == 200:
        data = response.text
        json_data = json.loads(data)

        # Define file paths
        host_ip_file = local_remote_path + 'hostname_ipaddress.yml'
        ip_host_file = local_remote_path + 'ipaddress_hostname.yml'
        deviceid_host_file = local_remote_path + 'deviceid_host.yml'
        deviceid_ip_file = local_remote_path + 'deviceid_ip.yml'

        # Open the necessary files for writing
        with open(host_ip_file, 'w+') as host_ip, \
             open(ip_host_file, 'w+') as ip_host, \
             open(deviceid_host_file, 'w+') as deviceid_host, \
             open(deviceid_ip_file, 'w+') as deviceid_ip:

            # Process each device and write to files
            for device in json_data['result_set']:
                hostname = json_data['result_set'][device]['name'].split(":")[0]
                ip = json_data['result_set'][device]['ip']
                nodeid = device.split("/")[-1]

                deviceid_host.write('"' + hostname + '": "' + nodeid + '"\n')
                deviceid_ip.write('"' + ip + '": "' + nodeid + '"\n')

                if hostname and ip:
                    host_ip.write('"' + hostname + '": "' + ip + '"\n')
                    ip_host.write('"' + ip + '": "' + hostname + '"\n')

                #print("host_ip: " + hostname + ", ip_host: " + ip + ", deviceid_host: " + nodeid)
# Call the function to fetch, process, and transfer the device data
fetch_process_and_transfer_device_data()

# Transfer all files

files_to_transfer = [hostname_class_file, ip_class_file, id_class_file, host_ip_file, ip_host_file, deviceid_host_file, deviceid_ip_file]

for hostname in hostnames:
    ssh, sftp = create_sftp_client(hostname, elk_username, elk_password)
    if sftp:
        try:
            for file_path in files_to_transfer:
                try:
                    # Extracting the file name from the file path using string manipulation
                    file_name = file_path.split('/')[-1]  # Assumes '/' as the path separator
                    sftp.put(file_path, remote_path_file + file_name)
                    logger.info("Successfully transferred " + file_path + " to " + hostname)
                except Exception as e:
                    logger.error("Failed to transfer " + file_path + " to " + hostname + ": " + str(e))
        except Exception as e:
            logger.error("Failed to transfer files to " + hostname + ": " + str(e))
        finally:
            sftp.close()
            ssh.close()
    else:
        logger.error("Failed to create SFTP client for hostname: " + hostname)