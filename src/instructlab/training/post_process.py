import re
import sys
import statistics

def parse_line(line):
    # Define a regular expression pattern to match the key-value pairs
    pattern = r"(\w+):\s*([\d.]+)|(\w+)\s*=\s*([\d.]+)"
    if "Epoch:" not in line and "epoch=" not in line:
        return None
    
    line = line.strip().lower()
    line = line.replace('.. ', ',')

    # Use re.findall to extract all matches
    matches = re.findall(pattern, line)
    
    # Create a dictionary to store the parsed values
    parsed_data = {}
    
    for match in matches:
        # Each match is a tuple with two possible groups
        key = match[0] or match[2]
        value = match[1] or match[3]
        
        # Convert value to float if it contains a decimal point, otherwise to int
        if '.' in value:
            value = float(value)
        else:
            value = int(value)
        
        # Store the key-value pair in the dictionary
        parsed_data[key] = value
    
    return parsed_data

def parse_file(filename):
    entries = {}
    with open(filename, 'r') as file:
        for line in file:
            line_dict = parse_line(line) 
            if not line_dict:
                continue
            key = (line_dict['epoch'], line_dict['step'], line_dict['rank'])
            if key not in entries:
                entries[key] = line_dict
            else:
                entries[key].update(line_dict)
    return entries

def get_summary(entries, key='rank'):
    unique_values = set(entries[hash][key] for hash in entries)

    for target in unique_values:
        fwd_pass_times = []
        bwd_pass_times = []
        fullstep_times = []
        for hash, line_dict in entries.items():
            if line_dict[key] == target:
                fwd_pass_times.append(line_dict['fwd_pass_elapsed_time'])
                bwd_pass_times.append(line_dict['bwd_elapsed_time'] - line_dict['post_reduce_elapsed_time'])
                fullstep_times.append(line_dict['loop_end_time'])

        print(f"{key} {target}: FWD Pass (seconds): Average = {statistics.mean(fwd_pass_times):.2f}, Median = {statistics.median(fwd_pass_times):.2f}, Min = {min(fwd_pass_times):.2f}, Max = {max(fwd_pass_times):.2f}")
        print(f"{key} {target}: BWD Pass (seconds): Average = {statistics.mean(bwd_pass_times):.2f}, Median = {statistics.median(bwd_pass_times):.2f}, Min = {min(bwd_pass_times):.2f}, Max = {max(bwd_pass_times):.2f}")
        print(f"{key} {target}: StepTime (seconds): Average = {statistics.mean(fullstep_times):.2f}, Median = {statistics.median(fullstep_times):.2f}, Min = {min(fullstep_times):.2f}, Max = {max(fullstep_times):.2f}")


def main():
    if len(sys.argv) != 2:
        print("Usage: python post_process.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    entries = parse_file(filename)
    
    get_summary(entries)

if __name__ == "__main__":  
    main()