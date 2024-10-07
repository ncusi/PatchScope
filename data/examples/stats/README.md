# Example data - statistics extracted from patch annotations

This directory contains JSON files generated with `diff-gather-stats`
script and its various subcommand, processing the output of running
`diff-annotate from-repo` command.

Those files are being analyzed by Jupyter notebooks in the
[`/notebooks/`](../../../notebooks) directory.


## Projects and repositories

The list of different example repositories taken into considerations
is borrowed from the [GitVision app demo site](https://gitvis.web.app/).

- Large repositories:
  - [TensorFlow](https://github.com/tensorflow/tensorflow): A comprehensive machine learning library by Google<br>
    This repo provides a great example of a large, complex open-source project with a very active community.
  - ...

Repositories are cloned into `/mnt/data/jnareb/example_repositories/`
on `przybysz` (access via SSH on VPN).


## Generating annotation data

The annotation data for further processing is generated directly from the repo
in the "flat" format.  It was generated with the following command:
```commandline
diff-annotate from-repo \
  --output-dir=~/example_annotations/tensorflow/ezhulenev/ \
  ~/example_repositories/tensorflow/ \
  --author=ezhulenev@google.com
```
and
```commandline
diff-annotate from-repo \
  --output-dir=~/example_annotations/tensorflow/yong.tang/ \
  ~/example_repositories/tensorflow/ \
  --author=yong.tang.github@outlook.com
```

The "flat" format has the following structure:
`<output_dir>/<commit_id>.json`.

## Generating stats data

Statistics computed from annotations were saved in JSON files, one single
file per different type of statistics.

- `tensorflow.purpose-per-file.json` (1.8 MB) was generated with the following command:

    ```commandline
    diff-gather-stats --annotations-dir='' \
      purpose-per-file \
      ~/example_annotations/tensorflow.purpose-per-file.json \
      ~/example_annotations/tensorflow/
    ```

- `tensorflow.lines-stats.json` (9.8 MB) was generated with the following command:

    ```commandline
    diff-gather-stats --annotations-dir='' \
      lines-stats \
      ~/example_annotations/tensorflow.lines-stats.json \
      ~/example_annotations/tensorflow/
    ```

- `tensorflow.timeline.json` (3.2 MB) was generated with the following command:

    ```commandline
    diff-gather-stats --annotations-dir='' \
      timeline \
      ~/example_annotations/tensorflow.timeline.json \
      ~/example_annotations/tensorflow/
    ```

- `tensorflow.timeline.purpose-to-type.json` (3.2 MB) was generated with
  the following command:

    ```commandline
    diff-gather-stats --annotations-dir='' \
      timeline \
      --purpose-to-annotation=data \
      --purpose-to-annotation=documentation \
      --purpose-to-annotation=markup \
      --purpose-to-annotation=other \
      --purpose-to-annotation=project \
      --purpose-to-annotation=test \
      ~/example_annotations/tensorflow.timeline.purpose-to-type.json \
      ~/example_annotations/tensorflow/
    ```

