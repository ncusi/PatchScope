def line_callback(file_purpose, tokens):
    # NOTE: function definition *must* currently be first line of the file

    # based on the code used to generate initial annotations for HaPy-Bug
    # https://github.com/ncusi/python_cve_dataset/blob/main/annotation/annotate.py#L80

    #print(f"RUNNING line_callback({file_purpose!r}, ...) -> {''.join([t[2] for t in tokens]).rstrip()}")
    line_type = file_purpose

    # the original code uses file _type_ here (the "type" field in 'languages.yml');
    # file purpose is here often the same as file type, but not always (!)
    # see Languages._path2purpose(path: str, filetype: str) -> str
    if file_purpose != "programming":
        if file_purpose not in ["documentation", "test"]:
            line_type = "bug(fix)"
    else:
        # For programming languages
        if line_is_comment(tokens):
            line_type = "documentation"
            #print(f"  line is comment, {file_purpose=}, {line_type=}")
        elif file_purpose == "test":
            line_type = "test"
        else:
            line_type = "bug(fix)"

    #print(f"  returning {line_type=}")
    return line_type
