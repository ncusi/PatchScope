def line_callback(file_data, tokens):
    # NOTE: function definition *must* currently be first line of the file

    # based on the code used to generate initial annotations for HaPy-Bug
    # https://github.com/ncusi/python_cve_dataset/blob/main/annotation/annotate.py#L80

    #print(f"RUNNING line_callback({file_data!r}, ...) -> {''.join([t[2] for t in tokens]).rstrip()}")
    line_type = file_data['purpose']

    if file_data['type'] != "programming":
        if file_data['purpose'] not in ["documentation", "test"]:
            line_type = "bug(fix)"
    else:
        # For programming languages
        if line_is_comment(tokens):
            line_type = "documentation"
            #print(f"  line is comment, {file_data=}, {line_type=}")
        elif file_data['purpose'] == "test":
            line_type = "test"
        else:
            line_type = "bug(fix)"

    #print(f"  returning {line_type=}")
    return line_type
