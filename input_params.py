[
  {"name": "db_cred_id", "type": "number", "required": true},
  {"name": "elk_cred_id", "type": "number", "required": true},
  {"name": "sl_api_cred_id", "type": "number", "required": true},
  {"name": "debug_mode", "type": "boolean", "required": false, "default": false},
  {"name": "elk_hosts", "type": "string", "required": true, "default": "192.168.2.167, 192.168.2.168, 192.168.2.169"},
  {"name": "log_file_path", "type": "string", "required": true, "default": "/data/logs/sl_data_elk_yaml.log"},
  {"name": "sl_remote_path", "type": "string", "required": true, "default": "/tmp/"},
  {"name": "elk_remote_path", "type": "string", "required": true, "default": "/opt/elk/logstash/config/enrichment_sl/"},
  {"name": "fn_host_class", "type": "string", "required": true, "default": "hostname_class.yml"},
  {"name": "fn_ip_class", "type": "string", "required": true, "default": "ipaddress_class.yml"},
  {"name": "fn_id_class", "type": "string", "required": true, "default": "deviceid_class.yml"},
  {"name": "fn_host_ip", "type": "string", "required": true, "default": "hostname_ipaddress.yml"},
  {"name": "fn_ip_host", "type": "string", "required": true, "default": "ipaddress_hostname.yml"},
  {"name": "fn_id_host", "type": "string", "required": true, "default": "deviceid_host.yml"},
  {"name": "fn_id_ip", "type": "string", "required": true, "default": "deviceid_ip.yml"}
]