import re

def extract_placeholders(format_string, file_name):
    # Find all placeholders using regular expression
    placeholders = re.findall(r"\{(.*?)\}", format_string)
    # Initialize a dictionary to store the extracted values
    params = {}
    
    # Extract the values from the given file name
    for placeholder in placeholders:
        try:
            # Try different patterns to extract values
            patterns = [
                f"{placeholder}_(.*?)_",  # Original pattern
                f"{placeholder}=(.*?)_",  # Alternative pattern with equals
                f"{placeholder}-(.*?)_",  # Pattern with dash
            ]
            
            value = None
            for pattern in patterns:
                match = re.search(pattern, file_name)
                if match:
                    value = match.group(1)
                    break
            
            if value is None:
                # Try to extract from end of filename before extension
                end_pattern = f"{placeholder}_(.*?)\\.csv"
                match = re.search(end_pattern, file_name)
                if match:
                    value = match.group(1)
            
            if value is not None:
                # Convert to integer if possible
                if value.isdigit():
                    params[placeholder] = int(value)
                else:
                    params[placeholder] = value
            else:
                # Placeholder not found in the file name
                params[placeholder] = None
                
        except AttributeError:
            # Placeholder not found in the file name
            params[placeholder] = None

    return params

def extract_config_from_filename(filename):
    """Extract configuration parameters from modern traffic trace filenames.
    
    Handles filenames like:
    - traffic_trace_slimfly.csv
    - traffic_FFT3D_nx100_RRG_source_routing.csv
    - trace_V36_D5_EPR3.csv
    """
    config = {}
    
    # Extract common patterns
    patterns = {
        'V': r'V(\d+)',
        'D': r'D(\d+)', 
        'EPR': r'EPR(\d+)',
        'TOPO': r'_(\w+)topo|_(slimfly|dragonfly|fattree|jellyfish|polarfly)_',
        'ROUTING': r'_(source_routing|dest_tag|nonadaptive|adaptive|ugal)',
        'BENCH': r'_(FFT3D|Allreduce|Alltoall|uniform|shift)_'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            # Get the first non-None group (handles alternation patterns)
            value = None
            for i in range(1, len(match.groups()) + 1):
                if match.group(i) is not None:
                    value = match.group(i)
                    break
            
            if value is not None:
                if value.isdigit():
                    config[key] = int(value)
                else:
                    # Normalize topology names to lowercase for consistency
                    if key == 'TOPO':
                        config[key] = value.lower()
                    else:
                        config[key] = value
            else:
                config[key] = None
        else:
            config[key] = None
            
    return config

    # example usage:
    # format_string = "traffic_BENCH_{BENCH}_EPR_{EPR}_ROUTING_{ROUTING}_V_{V}_D_{D}_TOPO_{TOPO}_SUFFIX_{SUFFIX}_.csv"
    # file_name = "traffic_BENCH_1_EPR_2_ROUTING_3_V_4_D_5_TOPO_6_SUFFIX_7_.csv"
    # extracted_values = extract_placeholders(format_string, file_name)
    

    # result should be : {'BENCH': 1, 'EPR': 2, 'ROUTING': 3, 'V': 4, 'D': 5, 'TOPO': 6, 'SUFFIX': 7}