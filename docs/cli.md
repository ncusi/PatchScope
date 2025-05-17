# CLI Reference

This page provides documentation for PatchScope command line tools.

The PatchScope includes four key elements, each with the corresponding 
CLI (Command Line Interface) tool:

1. extracting patches from a version control system or user-provided folders<br>
   either as separate step with [`diff-generate`](#diff-generate),
   or integrated into the annotation step ([`diff-annotate`](#diff-annotate))
2. applying specified annotation rules for selected patches<br>
   using [`diff-annotate`](#diff-annotate), which generates one JSON data file per patch
3. generating configurable reports or summaries<br>
   with various subcommands of [`diff-gather-stats`](#diff-gather-stats);
   each summary is saved as a single JSON file
4. advanced visualization with a web application (dashboard),<br>
   (using the summaries generated in the previous step), 
   which you can run it with `panel serve`, or [`diffinsights-web`](#diffinsights-web)

[//]: # (see https://github.com/syn54x/mkdocs-typer2)

::: mkdocs-typer2
    :module: diffannotator.generate_patches
    :name: diff-generate

::: mkdocs-typer2
    :module: diffannotator.annotate
    :name: diff-annotate

::: mkdocs-typer2
    :module: diffannotator.gather_data
    :name: diff-gather-stats

<hr>

::: mkdocs-typer2
    :module: diffinsights_web.main
    :name: diffinsights-web
