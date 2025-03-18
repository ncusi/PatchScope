from collections import Counter
from io import StringIO
from pathlib import Path
from textwrap import dedent
from typing import Optional

# data analysis
import pandas as pd
# dashboard
import panel as pn
import param
from panel_mermaid import MermaidDiagram

from diffinsights_web.apps.author import get_authors
from diffinsights_web.datastore import find_dataset_dir
from diffinsights_web.datastore.linesstats import get_lines_stats_data
from diffinsights_web.datastore.timeline import (find_timeline_files, get_timeline_data,
                                                 find_repos, get_timeline_df)

pn.extension()

# See https://mermaid.js.org/schemas/config.schema.json
class MermaidSankeyConfiguration(pn.viewable.Viewer, pn.widgets.WidgetBase):
    """An interactive Widget for editing the Mermaid JS configuration for Sankey diagram.

    See https://mermaid.js.org/schemas/config.schema.json
    See https://mermaid.js.org/config/schema-docs/config.html#definitions-group-sankeydiagramconfig

    Example:

    >>> config = MermaidSankeyConfiguration()

    You can use it as a *reference value* for the MermaidDiagram:

    >>> diagram = MermaidDiagram(
    ...    object="sankey-beta\\n\\n%% source,target,value\\n...",
    ...    configuration=config,
    ... )
    """
    # based on MermaidConfiguration from panel_mermaid
    # https://github.com/awesome-panel/panel-mermaid/blob/main/src/panel_mermaid/mermaid.py
    value: dict = param.Dict(
        constant=True,
        doc="""The Mermaid JS configuration for Sankey diagram.""",
    )

    showValues: bool = param.Boolean(
        default=True,
        doc="""Toggle to display or hide values along with title."""
    )
    linkColor: str = param.Selector(
        default="gradient",
        objects=["source", "target", "gradient"],
        doc=dedent(
            """
            The color of the links in the Sankey diagram:

            - `source` - link will be of a source node color
            - `target` - link will be of a target node color
            - `gradient` - link color will be smoothly transient between source and target node colors
            - hex code of color, like `#a1a1a1` (unsupported)
            """
        )
    )
    nodeAlignment: str = param.Selector(
        default="justify",
        objects=["left", "right", "center", "justify"],
        doc=dedent(
            """
            Defines graph layout of Sankey diagram:

            - `left` - Align all inputs to the left.
            - `right` - Align all outputs to the right.
            - `center` - Like `left`, except that nodes without any incoming links are moved as right as possible.
            - `justify` - Like `left`, except that nodes without any outgoing links are moved to the far right.
            """
        )
    )
    width: int = param.Integer(
        default=600,
        bounds=(0, None),
        doc="""Height of the diagram""",
    )
    height: int = param.Integer(
        default=400,
        bounds=(0, None),
        doc="""Width of the diagram""",
    )
    useMaxWidth: bool = param.Boolean(
        default=False,
        doc=dedent(
            """\
            When this flag is set to `True`, the height and width is set to 100%
            and is then scaled with the available space.
            If set to `False`, the absolute space required is used.
            """
        ),
    )
    prefix: str = param.String(
        default="",
        doc="""The prefix to use for values""",
    )
    suffix: str = param.String(
        default="",
        doc="""The suffix to use for values""",
    )

    def __init__(self, **params):
        super().__init__(**params)

    @param.depends(
        "showValues", "linkColor", "nodeAlignment",
        "useMaxWidth", "width", "height", "prefix", "suffix",
        watch=True, on_init=True
    )
    def _update_value(self):
        value = {
            'sankey': {
                "showValues": self.showValues,
                "linkColor": self.linkColor,
                "nodeAlignment": self.nodeAlignment,
                "useMaxWidth": self.useMaxWidth,
                "width": self.width,
                "height": self.height,
                "prefix": self.prefix,
                "suffix": self.suffix,
            },
        }
        value['sankey'] = {
            key: val
            for key, val in value['sankey'].items()
            if val is not None and val != self.param[key].default
        }
        if not value['sankey']:
            value = {}

        with param.edit_constant(self):
            self.value = value

    def widgets(self):
        return [
            self.param.showValues,
            self.param.linkColor,
            self.param.nodeAlignment,
            self.param.useMaxWidth,
            self.param.width,
            self.param.height,
            self.param.prefix,
            self.param.suffix,
        ]

    def __panel__(self):
        return pn.Column(
            *self.widgets()
        )


# ---------------------------------------------------------------------------
# widgets from diffinsights_web.app.author
dataset_dir = find_dataset_dir()
select_file_widget = pn.widgets.Select(
    name="input JSON file",
    options=find_timeline_files(dataset_dir),
    value=str(dataset_dir.joinpath('qtile.timeline.purpose-to-type.json')),
)

get_timeline_data_rx = pn.rx(get_timeline_data)(
    json_path=select_file_widget,
)

find_repos_rx = pn.rx(find_repos)(
    timeline_data=get_timeline_data_rx,
)
repos_widget = pn.widgets.Select(
    name="repository",
    options=find_repos_rx,
    value="qtile",
    disabled=find_repos_rx.rx.pipe(len) <= 1,
)

get_timeline_df_rx = pn.rx(get_timeline_df)(
    json_path=select_file_widget,
    timeline_data=get_timeline_data_rx,
    repo=repos_widget,
)

author_column = 'author.email'
authors_rx = pn.rx(get_authors)(
    tf_timeline_df=get_timeline_df_rx,
)
authors_widget = pn.widgets.Select(
    name="author",
    value="tycho@tycho.ws",  # author.email
    options=authors_rx
)


# function that returns filtered (but not resampled) data
#@pn.cache
def tf_timeline_df_author(tf_timeline_df: pd.DataFrame, author: str) -> pd.DataFrame:
    return tf_timeline_df[tf_timeline_df[author_column] == author]


# ----------------------------------------------------------------------------
# widgets from diffinsights_web.datastore.linesstats.LinesStatsDataStore
lines_stats_data_rx = pn.rx(get_lines_stats_data)(
    dataset_dir=dataset_dir,  # does not change, no need for rx
    timeseries_file=select_file_widget,
)


# ............................................................................
# new functions
#@pn.cache
def author_patch_ids(tf_timeline_df: pd.DataFrame, author: str) -> set[str]:
    return set(tf_timeline_df[tf_timeline_df[author_column] == author]['patch_id'].tolist())


def triples_from_counter(data_counter: Counter) -> list[tuple[str, str, int]]:
    return [(p[0], p[1], v) for p, v in data_counter.items()]


# code borrowed from diffinsights_web.datastore.linesstats.count_file_x_line_in_lines_stats
def line_stats_to_per_author_counter(lines_stats_data: dict,
                                     change_type: str = "+/-",
                                     prefix: str = 'type.',
                                     patch_id_set: Optional[set] = None) -> Optional[Counter]:
    if lines_stats_data is None:
        return None

    result = Counter()

    for dataset, dataset_data in lines_stats_data.items():
        print(f"line_stats...: {dataset=}")  # e.g. "data/examples/annotations/qtile"
        for bug_or_repo, lines_data in dataset_data.items():
            print(f"line_stats...: {bug_or_repo=}")  # e.g. "all_authors-no_merges"
            for patch_file, patch_data in lines_data.items():

                if patch_id_set is not None and patch_file not in patch_id_set:
                    continue

                for file_name, file_data in patch_data.items():
                    if change_type not in file_data:
                        continue

                    for line_info, n_lines in file_data[change_type].items():
                        if not line_info.startswith(prefix):
                            continue

                        result[(file_name, line_info)] += n_lines

    return result


def counter_get_split_dirs_counter(data_counter: Optional[Counter]) -> Optional[Counter]:
    if data_counter is None:
        return None

    dir_data = Counter()

    for n_pair, value in data_counter.items():
        file_name, _ = n_pair  # n_pair is (file_name, line_type)
        # print(f"{p} => {v}")
        dir_data[(str(Path(file_name).parent), file_name)] += value
        for p_f, p_t in zip(Path(file_name).parent.parents, Path(file_name).parents):
            # print(f"- ({p_f}, {p_t})")
            dir_data[(str(p_f), str(p_t))] += value

    return dir_data


def counter_add_split_dirs_counter(data_counter: Optional[Counter]) -> Optional[Counter]:
    if data_counter is None:
        return None

    return data_counter | counter_get_split_dirs_counter(data_counter)


# instead of displaying full information about changed lines in changed files,
# can consider changes in aggregate (aggregating into containing directory).
def counter_file_to_containing_dir(data_counter: Optional[Counter],
                                   prefix: str = 'type.') -> Optional[Counter]:
    if data_counter is None:
        return None

    result = Counter()
    replace = {}

    # find replacements
    for n_pair, value in data_counter.items():
        (n_from, n_to) = n_pair

        # NOTE: a bit fragile, but should work
        # TODO: replace with a better method
        if n_to.startswith(prefix):
            replace[n_from] = f"{Path(n_from).parent}/*"

    # replace in both n_from and n_to
    for n_pair, value in data_counter.items():
        (n_from, n_to) = n_pair
        n_from = replace.get(n_from, n_from)
        n_to   = replace.get(n_to,   n_to)

        result[(n_from, n_to)] += value

    return result


def path_depth(path: str) -> int:
    """Return number of components in UNIX path stored as string

    Treat '.' as root, with depth 0.  Treat any path without '/' as having
    depth 1; each subsequent '/' means new component.

    :param path: relative UNIX pathname
    :return: depth of pathname
    """
    if path == ".":
        return 0
    else:
        return path.count('/') + 1


def path_depth_adj(path: str) -> int:
    """Like `path_depth`, but consider depth of 'path' and 'path/*' to be the same

    :param path: relative UNIX pathname
    :return: adjusted depth of pathname
    """
    if path == ".":
        return 0
    else:
        return path.count('/') + 1 - int(path.endswith('/*'))


def shorten_path_repl(path: str, max_len: int) -> str:
    """Shorten path to `max_len` components, suffix with '/**' it if it was shortened

    Examples:

    >>> shorten_path_repl('A/B/C/D/E/F', 2)
    'A/B/**'
    >>> shorten_path_repl('A/B', 2)
    'A/B'

    :param path: relative UNIX pathname
    :param max_len: maximum number of components
    :return: pathname with up to `max_len` components
    """
    if path.count('/') >= max_len:
        return '/'.join(path.split(sep='/', maxsplit=max_len)[:max_len] + ['**'])
    else:
        return path


def path_parent(path: str) -> str:
    """Same as str(PurePath(path).parent), but without wrapping.

    Assumes `path` is POSIX pathname, with '/' as directory separators.
    """
    last_slash = path.rfind('/')
    if last_slash < 0:
        return '.'
    else:
        return path[:last_slash]


def simplify_sankey_forward_depth(data_counter: Optional[Counter],
                                  depth_limit: int,
                                  prefix: str = 'type.') -> Optional[Counter]:
    if data_counter is None:
        return None

    result = Counter()

    for n_pair, value in data_counter.items():
        (n_from, n_to) = n_pair

        # print(f"{n_from} ={value}=> {n_to}: ", end="")

        if n_to.startswith(prefix):
            if path_depth_adj(n_from) <= depth_limit:
                # print("(kept)")
                result[n_pair] += value
            else:
                # print(f"{shorten_path_repl(n_from, depth_limit)} ===> {n_to}")
                result[(shorten_path_repl(n_from, depth_limit), n_to)] += value

        elif path_depth_adj(n_to) <= depth_limit:
            # NOTE: always path_depth_adj(n_from) < path_depth_adj(n_to) if n_to is path
            result[n_pair] += value
            # print(f"sum={result[n_pair]}")
        elif path_depth_adj(n_from) <= depth_limit:
            # print(f"{n_from} ---> {shorten_path_repl(n_to, depth_limit)}")
            result[n_from, (shorten_path_repl(n_to, depth_limit))] += value
        else:
            # print("(skipped)")
            pass

    return result


def simplify_sankey_forward_width_ast(data_counter: Optional[Counter],
                                      width_limit: int,
                                      prefix: str = 'type.') -> Optional[Counter]:
    if data_counter is None:
        return None

    result = Counter()
    to_delete = []

    # sort to operate forward
    data_list = sorted(
        triples_from_counter(data_counter),
        key=lambda triple: path_depth(triple[0])
    )

    for (n_from, n_to, value) in data_list:
        if not n_to.startswith(prefix) and value <= width_limit:
            # TODO: optimize
            for candidate in to_delete:
                if n_to.startswith(candidate):
                    break
            else:
                to_delete.append(n_to)

    # print(f"{to_delete=}")

    for (n_from, n_to, value) in data_list:
        for n_del in to_delete:
            if n_to.startswith(n_del):
                # print(f" - {n_from} ===> {n_to} ({value}) deleted due to {n_del}")
                break
            elif n_to.startswith('type.'):
                if n_from.startswith(n_del):
                    # print(f" * {path_parent(n_del)} ===> {n_del} ===> ... ===> {n_to} ({value})")
                    n_del_parent = path_parent(n_del)
                    n_del_ast = f"{n_del_parent}/**"
                    result[(n_del_parent, n_del_ast)] += value
                    result[(n_del_ast, n_to)] += value
                    break
        else:
            result[(n_from, n_to)] += value

    return result


def triples_to_csv(data_list: list[tuple[str, str, int]]) -> str:
    result = ['%% source,target,value']

    for f,t,v in data_list:
        result.append(f"{f},{t},{v}")

    return "\n".join(result) + "\n"


# ............................................................................
# new widgets


# ............................................................................
# new reactive components
author_patch_ids_rx = pn.rx(author_patch_ids)(
    tf_timeline_df=get_timeline_df_rx,
    author=authors_widget,
)


# ============================================================================
# main

configuration = MermaidSankeyConfiguration(
    showValues = False,
)
diagram = MermaidDiagram(
    object=dedent(
        """
        sankey-beta

        %% source,target,value
        Electricity grid,Over generation / exports,104.453
        Electricity grid,Heating and cooling - homes,113.726
        Electricity grid,H2 conversion,27.14
        """
    ),
    configuration=configuration,
    update_value=True,
    width=800,
    height=400,
)

diagram = pn.FlexBox(
    configuration,
    pn.Column(
        diagram,
        #diagram.param.update_value,
        pn.widgets.FileDownload(
            file=pn.bind(StringIO, diagram.param.value), filename="diagram.svg"
        ),
    ),
)

# ---------------------------------------------------------------------------
# main app
template = pn.template.MaterialTemplate(
    site="PatchScope",
    title="Author Sankey Diagram",
    favicon="favicon-author.svg",
    sidebar_width=350,
    collapsed_sidebar=False,
    sidebar=[
        select_file_widget,
        repos_widget,
        authors_widget,
    ],
    main=[
        diagram,
    ],
)

template.servable()

if __name__ == "__main__":
    # Optionally run the application in a development server
    pn.serve(template, show=True)

