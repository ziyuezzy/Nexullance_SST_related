
import os
import subprocess
import sys

# default_config_dict = {
#     'LOAD':1.0,
#     'UNIFIED_ROUTER_LINK_BW':16,  #Gbps
#     'V':36,
#     'D':5,
#     'topo_name':"RRG",
#     'paths':"ASP",
#     'routing_algo': "nonadaptive", # same for two subnets
#     'traffic_pattern': "uniform"
# }

def run_sst(config_dict: dict, config_file_path:str, template_file_path:str, num_threads:int = 8):
    # Define the filename for the duplicate file

    # first dump the config dict
    with open(config_file_path, 'w') as file:
        file.write("import numpy as np\n")
        file.write("config_dict = ")
        file.write(repr(config_dict))  # Writes the dictionary in a format that Python can interpret
        # Read the contents of the template file
        with open(template_file_path, 'r') as template_file:
            content = template_file.read()
            # Then write the duplicated contents to the new file
            file.write(content)

    # # Run a command and wait for it to complete
    # result = subprocess.run(["sst", config_file_path], capture_output=True, text=True)

    # # Print the output
    # print(result.stdout)

    # Start a process
    process = subprocess.Popen(["sst", "-n", f"{num_threads}", config_file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Capture output and errors
    stdout, stderr = process.communicate()

    print("Output:", stdout)     # Output: Hello from Popen!
    if stderr:
        print("Error:", stderr)      # Error: (empty if no error)

    
