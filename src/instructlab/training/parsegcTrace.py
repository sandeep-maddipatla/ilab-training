import re
from collections import defaultdict
import statistics

def parse_log_file(file_path):
    # Regular expression to match the log line format
    log_line_regex = re.compile(
        r'\[\d{2}:\d{2}:\d{2}\.\d{6}\]\[PASS_MANAGER\s+\]\[trace\]\[tid:[0-9A-F]+\] Total time for (\w+): ([\d\.]+) seconds'
    )

    # Dictionary to store pass statistics
    pass_stats = defaultdict(list)

    # Read the log file
    with open(file_path, 'r') as file:
        for line in file:
            match = log_line_regex.match(line)
            if match:
                pass_name = match.group(1)
                time_seconds = float(match.group(2))
                pass_stats[pass_name].append(time_seconds)

    # Calculate statistics for each pass
    pass_statistics = []
    for pass_id, (pass_name, times) in enumerate(pass_stats.items(), start=0):
        num_calls = len(times)
        total_time = sum(times)
        average_time = total_time / num_calls
        median_time = statistics.median(times)
        max_time = max(times)

        pass_statistics.append({
            'id': pass_id,
            'pass_name': pass_name,
            'num_calls': num_calls,
            'total_time': total_time,
            'average_time': average_time,
            'median_time': median_time,
            'max_time': max_time,
            'times': times  # Add times for histogram
        })

    # Sort by total time
    pass_statistics.sort(key=lambda x: x['total_time'], reverse=True)
    return pass_statistics

def print_statistics(pass_statistics):
    for stats in pass_statistics:
        print(f"Pass Name: {stats['pass_name']}, ID: {stats['id']}")
        print(f"  Number of Calls: {stats['num_calls']}")
        print(f"  Total Time: {stats['total_time']:.6f} seconds")
        print(f"  Average Time: {stats['average_time']:.6f} seconds")
        print(f"  Median Time: {stats['median_time']:.6f} seconds")
        print(f"  Maximum Time: {stats['max_time']:.6f} seconds")

        # Print text-based histogram (10 bins)
        times = stats['times']
        if len(times) > 0:
            min_time = min(times)
            max_time = max(times)
            if min_time == max_time:
                bins = [len(times)] + [0]*9
                bin_edges = [min_time + i for i in range(11)]
            else:
                bin_width = (max_time - min_time) / 10
                bin_edges = [min_time + i*bin_width for i in range(11)]
                bins = [0]*10
                for t in times:
                    # Find the right bin for t
                    if t == max_time:
                        bins[-1] += 1
                    else:
                        idx = int((t - min_time) / bin_width)
                        bins[idx] += 1
            print("  Histogram (10 bins):")
            for i in range(10):
                left = bin_edges[i]
                right = bin_edges[i+1]
                bar = bins[i]
                print(f"    [{left:.6f}, {right:.6f}): {bar}")
        print()

if __name__ == "__main__":
    log_file_path = 'graph_compiler.log'
    pass_statistics = parse_log_file(log_file_path)
    print_statistics(pass_statistics)