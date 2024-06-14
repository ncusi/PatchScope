from pygments import lex
from pygments.lexers import CLexer
from collections import defaultdict, deque

# Example code to be tokenized
code = '''
 /**
  * brief       Calculate approximate memory requirements for raw encoder
  *
  * This function can be used to calculate the memory requirements for
  * Block and Stream encoders too because Block and Stream encoders don't
  * need significantly more memory than raw encoder.
  *
  * \param       filters     Array of filters terminated with
  *                          .id == LZMA_VLI_UNKNOWN.
  *
  * return      Number of bytes of memory required for the given
- *              filter chain when encoding. If an error occurs,
- *              for example due to unsupported filter chain,
- *              UINT64_MAX is returned.
+ *              filter chain when encoding or UINT64_MAX on error.
  */
'''

# Create a lexer instance
lexer = CLexer()

tokens = deque(lexer.get_tokens_unprocessed(code))
lines_tokens = defaultdict(list)


def map_code_to_tokens(code, tokens):
    idx_code = [i+1 for i, ltr in enumerate(code) if ltr == "\n"]
    lines = defaultdict(list)
    for no, idx in enumerate(idx_code):
        while tokens:
            token = tokens.popleft()
            if token[0] < idx:
                lines[no].append(token)
            else:
                tokens.appendleft(token)
                break
        prev_idx = idx

    return lines

def fill_gaps_with_previous_value(d):
    if not d:
        return {}
    
    # Find the minimum and maximum keys
    min_key = min(d.keys())
    max_key = max(d.keys())

    # Create a new dictionary to store the result
    filled_dict = {}

    # Initialize the previous value
    previous_value = None

    # Iterate through the range of keys
    for key in range(min_key, max_key + 1):
        if key in d:
            previous_value = d[key]
        filled_dict[key] = previous_value

    return filled_dict

lines = fill_gaps_with_previous_value(map_code_to_tokens(code, tokens))


for k in lines:
    print(k, "\t\t\t\t\t\t", lines[k])
exit(0)




print(lines_numbers)

for token in tokens:
    pos = 0
    for i,l in enumerate(lines_numbers):
        if l >= token[0]:
            break
        pos = i+1
    lines[pos].append(token)

    continue


