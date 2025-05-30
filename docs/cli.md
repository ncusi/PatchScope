# CLI Reference

This page provides documentation for PatchScope command line tools.

The PatchScope includes four key elements, each with the corresponding 
CLI (Command Line Interface) tool:

1. extracting patches from a version control system or user-provided folders<br>
   either as separate step with [`diff-generate`](cli_reference/diff-generate.md),
   or integrated into the annotation step ([`diff-annotate`](cli_reference/diff-annotate.md))
2. applying specified annotation rules for selected patches<br>
   using [`diff-annotate`](cli_reference/diff-annotate.md), which generates one JSON data file per patch
3. generating configurable reports or summaries<br>
   with various subcommands of [`diff-gather-stats`](cli_reference/diff-gather-stats.md);
   each summary is saved as a single JSON file
4. advanced visualization with a web application (dashboard),<br>
   (using the summaries generated in the previous step), 
   which you can run it with `panel serve`, or [`diffinsights-web`](cli_reference/diffinsights-web.md)

[//]: # (see https://github.com/syn54x/mkdocs-typer2)

