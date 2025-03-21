def detect_all_whitespace_line(_file_data, tokens):
    if len(tokens) == 1 and tokens[0][2] == "\n":
        return "empty"
    elif all([token_type in Token.Text.Whitespace or
              token_type in Token.Text and text_fragment.isspace()
              for _, token_type, text_fragment in tokens]):
        return "whitespace"
    else:
        return None
