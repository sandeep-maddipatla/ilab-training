import re
import sys

losses = []
s_it_values = []
with open('result.log', 'r', encoding='utf-8') as f:
    for line in f:
        # Look for patterns like total_loss=1.234 or total_loss: 1.234
        match = re.search(r'total_loss[=:]\s*([0-9.]+)', line)
        if match:
            losses.append(match.group(1))
        
        # Look for patterns like s/it=123.45, s/it: 123.45, 10s/it, or 10 s/it
        match = re.search(r'(\d+(?:\.\d+)?)\s*s/it', line)
        if match:
            s_it_values.append(match.group(1))


print(','.join(losses))
print(f"Number of entries found: {len(losses)}")

print(','.join(s_it_values))
print(f"Number of entries found: {len(s_it_values)}")

results = []
rank = sys.argv[1] if len(sys.argv) > 1 else '0'  # Default to rank 3 if not provided

with open('result.log', 'r', encoding='utf-8') as f:
    for line in f:
        # Only process lines where rank = 3
        if f'rank={rank}' in line:
            # Try to extract the three columns
            match = re.search(
                r'num_loss_counted_tokens[=:]\s*(\d+).*?num_tokens[=:]\s*(\d+).*?micro_batch_size[=:]\s*(\d+)',
                line
            )
            if match:
                results.append((match.group(1), match.group(2), match.group(3)))
            if len(results) >= 30:
                break

# Print header
print("num_loss_counted_tokens,num_tokens,micro_batch_size")
for row in results:
    print(','.join(row))