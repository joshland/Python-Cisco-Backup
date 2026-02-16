from netmiko import ConnectHandler
from .lib import write_backup

# Gives us the information we need to connect to VyOS devices.
def backup(host, username, password):
    vyos = {
        "device_type": "vyos",
        "host": host,
        "username": username,
        "password": password,
    }
    # Creates the connection to the device.
    net_connect = ConnectHandler(**vyos)
    net_connect.enable()
    # Gets the running configuration.
    output = net_connect.send_command("show conf comm")
    # Gets and splits the hostname for the output file name.
    hostname = net_connect.find_prompt().replace("#", "").replace(">", "")
    if not hostname:
        hostname = net_connect.send_command("sh conf | grep host-name | awk {'print $2'}")
        hostname = hostname.split()
        hostname = hostname[0]
    # Creates the file name, which is the hostname, and the date and time.
    fileName = hostname
    write_backup(fileName, output, host)
    # For the GUI
    global gui_filename_output
    gui_filename_output = fileName
