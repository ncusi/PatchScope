import math
from collections import Counter
from io import StringIO
from pathlib import PurePosixPath
from textwrap import dedent
from typing import Optional, Any

# data analysis
import pandas as pd
# dashboard
import panel as pn
import param
from panel_mermaid import MermaidDiagram

from diffinsights_web.datastore.linesstats import get_lines_stats_data
from diffinsights_web.datastore.timeline import path_to_name


def author_patch_ids(tf_timeline_df: pd.DataFrame,
                     author: str,
                     author_column: str = 'author.email') -> set[str]:
    return set(tf_timeline_df[tf_timeline_df[author_column] == author]['patch_id'].tolist())


def triples_from_counter(data_counter: Counter) -> list[tuple[str, str, int]]:
    return [(p[0], p[1], v) for p, v in data_counter.items()]


def counter_from_triples(data_list: list[tuple[str, str, int]]) -> Counter:
    return Counter({(p_f, p_t): v for p_f, p_t, v in data_list})


# code borrowed from diffinsights_web.datastore.linesstats.count_file_x_line_in_lines_stats
def line_stats_to_per_author_counter(lines_stats_data: dict,
                                     change_type: str = "+/-",
                                     prefix: str = 'type.',
                                     patch_id_set: Optional[set] = None) -> Optional[Counter]:
    if lines_stats_data is None:
        return None

    result = Counter()

    for dataset, dataset_data in lines_stats_data.items():
        # `dataset` can be e.g. "data/examples/annotations/qtile"
        for bug_or_repo, lines_data in dataset_data.items():
            # `bug_or_repo` can be e.g. "all_authors-no_merges"
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
        dir_data[(str(PurePosixPath(file_name).parent), file_name)] += value
        for p_f, p_t in zip(PurePosixPath(file_name).parent.parents, PurePosixPath(file_name).parents):
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
            replace[n_from] = f"{PurePosixPath(n_from).parent}/*"

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

    ## DEBUG
    # max_depth = 0

    for n_pair, value in data_counter.items():
        (n_from, n_to) = n_pair

        # print(f"{n_from} ={value}=> {n_to}: ", end="")

        ## DEBUG
        # max_depth = max(max_depth, path_depth_adj(n_to))

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

    ## DEBUG
    # print(f"simplify depth: {depth_limit=}, {max_depth=}")

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

    # print(f"simplify width: {width_limit=}, {to_delete=}")

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


def line_stats_to_per_author_sankey_counter(lines_stats_data: Optional[dict],
                                            depth_limit: int,
                                            width_limit: int,
                                            change_type: str = "+/-",
                                            prefix: str = 'type.',
                                            patch_id_set: Optional[set] = None) -> Optional[Counter]:
    if lines_stats_data is None:
        return None

    user_counter = line_stats_to_per_author_counter(
        lines_stats_data=lines_stats_data,
        change_type=change_type,
        prefix=prefix,
        patch_id_set=patch_id_set
    )
    user_counter_split_dir = counter_add_split_dirs_counter(user_counter)
    user_counter_dirs_only = counter_file_to_containing_dir(user_counter_split_dir,
                                                            prefix=prefix)

    simplify_depth = simplify_sankey_forward_depth(
        user_counter_dirs_only,
        depth_limit=depth_limit,
        prefix=prefix)
    simplify_width = simplify_sankey_forward_width_ast(
        simplify_depth,
        width_limit=width_limit,
        prefix=prefix)

    return simplify_width


def triples_to_csv(data_list: list[tuple[str, str, int]]) -> str:
    result = ['%% source,target,value']

    for f,t,v in data_list:
        result.append(f"{f},{t},{v}")

    return "\n".join(result) + "\n"


def counter_to_csv_styled(data_counter: Optional[Counter],
                          prefix: str = 'type.',
                          root: Optional[str] = 'project',
                          type_format: Optional[str] = '[{}]',
                          drop_root: bool = False,
                          strip_type_prefix: Optional[bool] = None) -> str:
    if data_counter is None:
        return ""

    result = ['sankey-beta', '', '%% source,target,value']
    prefix_len = len(prefix)

    if type_format is not None and strip_type_prefix is None:
        strip_type_prefix = True

    for (f, t), v in data_counter.items():
        if f == '.':
            if drop_root:
                continue
            if root is not None:
                f = root

        if t.startswith(prefix):
            if strip_type_prefix:
                t = t[prefix_len:]
            if type_format is not None:
                t = type_format.format(t)

        result.append(f"{f},{t},{v}")

    return "\n".join(result) + "\n"


def count_types(data_counter: Optional[Counter],
                prefix: str = 'type.') -> Counter:
    result = Counter()

    if data_counter is None:
        return result

    for (_, n_to), val in data_counter.items():
        if n_to.startswith(prefix):
            result[n_to] += val

    return result


def count_lines(data_counter: Optional[Counter],
                prefix: str = 'type.') -> int:
    return count_types(data_counter=data_counter, prefix=prefix).total()


def propose_width_limit(data_counter: Optional[Counter],
                        prefix: str = 'type.') -> int:
    n_lines = count_lines(data_counter=data_counter, prefix=prefix)
    if n_lines > 0:
        x = 0.10*n_lines  # 10% total width / root width

        mult = 10 ** math.floor(math.log10(x))
        return int(math.floor(x / mult) * mult)
    else:
        return n_lines



# See https://mermaid.js.org/schemas/config.schema.json
class MermaidSankeyConfiguration(pn.viewable.Viewer, pn.widgets.WidgetBase):
    """An interactive Widget for editing the Mermaid JS configuration for Sankey diagram.

    See https://mermaid.js.org/schemas/config.schema.json
    See https://mermaid.js.org/config/schema-docs/config.html#definitions-group-sankeydiagramconfig

    Example:

    >>> sankey_config = MermaidSankeyConfiguration()

    You can use it as a *reference value* for the MermaidDiagram:

    >>> sankey_diagram = MermaidDiagram(
    ...    object="sankey-beta\\n\\n%% source,target,value\\n...",
    ...    configuration=sankey_config,
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

    def widgets(self) -> list[pn.viewable.Viewable]:
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


class MermaidSankeyPlot(pn.viewable.Viewer):
    dataset_dir = param.Foldername(
        constant=True,
        doc="Dataset directory with *.timeline.*.json files",
    )
    timeseries_file = param.String(
        allow_refs=True,  # to allow widgets and reactive expressions
        doc="Selected JSON file with timeline data to find lines-stats companion for",
    )
    timeline_df = param.ClassSelector(
        class_=pd.DataFrame,
        allow_refs=True,
        doc="Timeline data as DataFrame, to extract patches by selected author",
    )
    author_column = param.Selector(
        default='author.email',
        objects=['author.email', 'author.name', 'committer.email', 'committer.name'],
        doc="Column used to select author's contributions",
    )
    author = param.String(
        allow_None=False,
        allow_refs=True,  # to allow widgets and reactive expressions
        doc="Value used to select the author",
    )

    width = param.Integer(
        default=820,
        doc="diagram width"
    )
    height = param.Integer(
        default=400,
        doc="diagram height",
    )

    def __init__(self, **params):
        super().__init__(**params)

        # ---------------------------------------------------------------------
        # widgets
        self.change_type_widget = pn.widgets.Select(
            name="Change type",
            value="+/-",
            options=["+", "-", "+/-"],
        )
        self.depth_limit_widget = pn.widgets.IntInput(
            name="Maximum depth limit (cutoff)",
            value=1,  # for the case with drop_root_node=False
            start=0,
        )
        self.width_limit_widget = pn.widgets.IntInput(
            name="Minimum width limit (cutoff)",
            value=500,
            start=1,
        )
        self.root_node_name_widget = pn.widgets.TextInput(
            name="Root node name ('.')",
            value="project",
        )
        self.drop_root_widget = pn.widgets.Checkbox(
            name="Drop root node",
            value=False,
        )
        self.strip_type_prefix_widget = pn.widgets.Checkbox(
            name="Strip 'type.' prefix",
            value=True,
        )

        # ---------------------------------------------------------------------
        # reactive expressions

        self.lines_stats_data_rx = pn.rx(get_lines_stats_data)(
            dataset_dir=self.dataset_dir,  # does not change, no need for rx
            timeseries_file=self.timeseries_file,
        )
        self.author_patch_ids_rx = pn.rx(author_patch_ids)(
            tf_timeline_df=self.timeline_df,
            author=self.author,
        )
        self.sankey_counter_rx = pn.rx(line_stats_to_per_author_sankey_counter)(
            # reactive expressions
            lines_stats_data=self.lines_stats_data_rx,
            patch_id_set=self.author_patch_ids_rx,
            # widgets, defined earlier
            change_type=self.change_type_widget,
            depth_limit=self.depth_limit_widget,
            width_limit=self.width_limit_widget,
        )
        self.sankey_csv_rx = pn.rx(counter_to_csv_styled)(
            # reactive expressions
            data_counter=self.sankey_counter_rx,
            # widgets, defined earlier
            root=self.root_node_name_widget,
            drop_root=self.drop_root_widget,
            strip_type_prefix=self.strip_type_prefix_widget,
        )


        # --------------------------------------------------------------------
        # callbacks
        def propose_width_limit_cb(_new_val: Any = None):
            if self.lines_stats_data_rx.rx.value is not None:
                width_limit = propose_width_limit(self.sankey_counter_rx.rx.value)
                if width_limit > 0:
                    self.width_limit_widget.value = width_limit


        self.author_patch_ids_rx.rx.watch(propose_width_limit_cb)
        self.change_type_widget.param.watch(
            propose_width_limit_cb,
            ['value'], what='value',
            onlychanged=True,
        )

        # ====================================================================
        # main panels

        self.configuration = MermaidSankeyConfiguration(
            showValues=False,
            width=self.width,
            height=self.height,
        )
        self.diagram = MermaidDiagram(
            object=self.sankey_csv_rx,
            configuration=self.configuration,
            update_value=True,
            # sizing_mode='stretch_width',
            width=self.width,
            height=400,
            # center within its container
            styles={
                "margin-left": "auto",
                "margin-right": "auto",
            },
        )

        self.count_types_pane = self.lines_stats_data_rx.rx.is_not(None).rx.where(
            pn.pane.Str(
                pn.rx("{lines_changed} {change_type!r} lines changed").format(
                    lines_changed=pn.rx(count_lines)(
                        data_counter=self.sankey_counter_rx,
                    ),
                    change_type=self.change_type_widget,
                    #proposed=pn.rx(propose_width_limit)(
                    #    data_counter=self.sankey_counter_rx,
                    #),
                ),
            ),
            pn.Spacer(height=0)
        )

        self.diagram = pn.FlexBox(
            #self.configuration,
            pn.Column(
                pn.Spacer(height=15),
                self.diagram,
                # diagram.param.update_value,
                pn.Spacer(height=10),
                pn.widgets.FileDownload(
                    file=pn.bind(StringIO, self.diagram.param.value),
                    label="Download Sankey diagram",
                    filename=pn.rx(
                        "sankey_diagram-repo={repo}-user={user}-drop_root={root}-values={values}.svg"
                    ).format(
                        repo=pn.rx(path_to_name)(self.timeseries_file),
                        user=self.author,
                        root=self.drop_root_widget,
                        values=self.configuration.showValues,
                    ),
                    width=400,
                    align='center',
                ),
                # center within its container
                styles={
                    "margin-left": "auto",
                    "margin-right": "auto",
                },
            ),
            align_content='space-evenly',
        )
        self.no_diagram = pn.pane.HTML(
            pn.rx("No corresponding *.lines-stats.* file for {json_path!r}").format(
                json_path=self.timeseries_file,
            ),
            styles={'font-size': '12pt'},
            width=self.width,
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self.lines_stats_data_rx.rx.is_not(None).rx.where(
            self.diagram,
            self.no_diagram,
        )

    def widgets_process(self) -> list[pn.viewable.Viewable]:
        return [
            self.change_type_widget,
            self.depth_limit_widget,
            self.count_types_pane,
            self.width_limit_widget,
            self.drop_root_widget,
            self.root_node_name_widget,
            self.strip_type_prefix_widget,
        ]

    def widgets_mermaid(self) -> list[pn.viewable.Viewable]:
        return self.configuration.widgets()

    def widgets(self) -> list[pn.viewable.Viewable]:
        return [
            self.change_type_widget,
            self.depth_limit_widget,
            self.count_types_pane,
            self.width_limit_widget,
            self.drop_root_widget,
            self.configuration.param.showValues,
            self.configuration.param.prefix,
            self.configuration.param.suffix,
        ]
