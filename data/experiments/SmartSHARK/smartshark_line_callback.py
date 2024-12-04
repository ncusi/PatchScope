def line_callback(file_data, tokens):
    # NOTE: function definition *must* currently be first line of the file

    line_type = "bugfix"

    if file_data['type'] != "programming":
        if file_data['purpose'] not in ["documentation", "test"]:
            line_type = "bugfix"  # or "unrelated"
    else:
        # For programming languages
        if line_is_whitespace(tokens):
            line_type = "whitespace"
        elif line_is_comment(tokens):
            line_type = "documentation"  # or "test", for test files
        elif file_data['purpose'] == "test":
            line_type = "test"
        else:
            line_type = "bugfix"

    return line_type
