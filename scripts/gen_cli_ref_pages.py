"""Generate the CLI api_reference page."""
import tomllib
from pathlib import Path

import mkdocs_gen_files


nav = mkdocs_gen_files.Nav()

root = Path(__file__).parent.parent

# TODO: check if file exists, or use try-catch
with root.joinpath("pyproject.toml").open(mode="rb") as f:
    proj = tomllib.load(f)

top_nav = 'Command line tools'
nav[top_nav] = '../cli.md'

for name, func in proj['project']['scripts'].items():

    doc_path = Path(name).with_suffix(".md")
    full_doc_path = Path("cli_reference", doc_path)
    with mkdocs_gen_files.open(full_doc_path, "w") as doc_file:
        module = func.split(":", maxsplit=1)[0]
        print("::: mkdocs-typer2", file=doc_file)
        print(f"    :module: {module}", file=doc_file)
        print(f"    :name: {name}", file=doc_file)
        print("", file=doc_file)

    # for use together with section-index plugin
    #nav[top_nav, name] = doc_path.as_posix()
    # for use together without section-index plugin
    nav[name] = doc_path.as_posix()

with mkdocs_gen_files.open("cli_reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
