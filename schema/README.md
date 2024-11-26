# Schemas

This directory contains formal descriptions of various file format
used for development, used by the project, and created by the project.


## External schema - development

- [`dvc_yaml.schema.json`](./dvc_yaml.schema.json) is a [JSON Schema][]
  for [`dvc.yaml` file format][dvc_yaml-files] (that is used to define
  [DVC][] pipelines).  It can provide better autocompletion, validation,
  and linting for `dvc.yaml` files in IDEs like Visual Studio Code
  and JetBrain's PyCharm.

  Comes from <https://github.com/iterative/dvcyaml-schema>

[JSON Schema]: https://json-schema.org/
[dvc_yaml-files]: https://dvc.org/doc/user-guide/project-structure/dvcyaml-files
[DVC]: https://dvc.org/
