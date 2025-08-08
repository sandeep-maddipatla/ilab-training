import re
import statistics

logfile = "/app/ptbridge_op_exec_workstream/hs6285/result_4/logs/2/towl_log.txt"
start_line = 31555
byte_values = []

with open(logfile, "r") as f:
    for i, line in enumerate(f, 1):
        if i < start_line:
            continue
        match = re.search(r"\((\d+)\s*b\)", line)
        if match:
            x = int(match.group(1))
            byte_values.append(x)

print(f"byte_values: {byte_values}")
print(f"Count: {len(byte_values)}")
print(f"Sum: {sum(byte_values)} bytes ... {sum(byte_values)/1024/1024/1024:.2f} GB")
if byte_values:
    print(f"Min: {min(byte_values)}")
    print(f"Median: {statistics.median(byte_values)}")
    print(f"Average: {statistics.mean(byte_values):.2f}")
    print(f"Max: {max(byte_values)}")