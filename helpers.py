import re

def extract_placeholders(format_string, file_name):
    # Find all placeholders using regular expression
    placeholders = re.findall(r"\{(.*?)\}", format_string)
    # Initialize a dictionary to store the extracted values
    params = {}
    # Extract the values from the given file name
    for placeholder in placeholders:
        try:
            value = re.search(f"{placeholder}_(.*?)_", file_name).group(1)
            # Convert to integer if possible
            if value.isdigit():
                params[placeholder] = int(value)
            else:
                params[placeholder] = value
        except AttributeError:
            # Placeholder not found in the file name
            params[placeholder] = None

    return params
    # example usage:
    # format_string = "traffic_BENCH_{BENCH}_EPR_{EPR}_ROUTING_{ROUTING}_V_{V}_D_{D}_TOPO_{TOPO}_SUFFIX_{SUFFIX}_.csv"
    # file_name = "traffic_BENCH_1_EPR_2_ROUTING_3_V_4_D_5_TOPO_6_SUFFIX_7_.csv"
    # extracted_values = extract_placeholders(format_string, file_name)