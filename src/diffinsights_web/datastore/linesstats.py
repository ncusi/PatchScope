import json
from collections import Counter, defaultdict
from collections.abc import Container, Iterable
from pathlib import Path, PurePosixPath
from typing import Union, Optional

import pandas as pd
import panel as pn
import param


def get_lines_stats_data(dataset_dir: str, timeseries_file: str) -> Optional[dict]:
    timeseries_file_path = Path(timeseries_file)
    if not timeseries_file_path.is_file():
        # check if maybe `timeseries_file` is path relative to `dataset_dir`
        timeseries_file_path = Path(dataset_dir).joinpath(timeseries_file)

    dataset_dir = timeseries_file_path.parent
    lines_stats_file = timeseries_file_path.name.replace('.timeline.', '.lines-stats.')
    file_path = dataset_dir.joinpath(lines_stats_file)

    if file_path.is_file():
        with open(file_path, mode='r') as json_fp:
            return json.load(json_fp)
    else:
        return None


def count_file_x_line_in_lines_stats(lines_stats_data: Optional[dict],
                                     repo_name: str,
                                     change_type: str = "+/-",
                                     prefix: str = 'type.') -> Optional[Counter]:
    #print(f"count_file_line_in_lines_stats(..., {repo_name=}, {change_type=}, {prefix=})")
    if lines_stats_data is None:
        return None

    result = Counter()

    for dataset, dataset_data in lines_stats_data.items():
        for bug_or_repo, lines_data in dataset_data.items():
            if bug_or_repo != repo_name:
                #print(f"    - skipping: {bug_or_repo!r} != {repo_name!r}")
                continue

            for patch_file, patch_data in lines_data.items():
                for file_name, file_data in patch_data.items():
                    if change_type not in file_data:
                        continue

                    for line_info, n_lines in file_data[change_type].items():
                        if not line_info.startswith(prefix):
                            continue

                        result[(file_name, line_info)] += n_lines

    return result


def sorted_changed_files(lines_stats_counter: Optional[Counter]) -> Optional[list[str]]:
    if lines_stats_counter is None:
        return None

    counts = Counter()
    for kv, n_lines in lines_stats_counter.items():
        file_name = kv[0]
        counts[file_name] += n_lines

    return [elem[0] for elem in counts.most_common()]


def limit_count_to_selected_files(lines_stats_counter: Counter,
                                  files: Union[Container[str], Iterable[str]]) -> Counter:
    return Counter({
        kv: n_lines for kv, n_lines in lines_stats_counter.items()
        if kv[0] in files
    })


def sankey_triples_from_counter(data_counter: Counter) -> list[tuple[str, str, int]]:
    return [(p[0], p[1], v) for p, v in data_counter.items()]


def sankey_counter_from_triples(data_list: list[tuple[str, str, int]]) -> Counter:
    return Counter({(p_f, p_t): v for p_f, p_t, v in data_list})


def path_to_dirs_only_counter(data_counter: Counter) -> Counter:
    result = Counter()

    for (p, l), v in data_counter.items():
        #print(f"{p} ={v}=> {l}")
        p_path = PurePosixPath(p)
        result[(str(p_path.parent), l)] += v
        for p_f, p_t in zip(p_path.parent.parents, p_path.parents):
            #print(f"- ({p_f}, {p_t})")
            result[(str(p_f), str(p_t))] += v

    return result


def add_dashdash_dirs_to_counter(data_counter: Counter) -> Counter:
    res = data_counter.copy()

    xsankey_data_sets = {
        'dir-to-dir': set(),
        'dir-to-line': set(),
    }
    #xsankey_data_cntr = Counter()
    xsankey_data_line = defaultdict(set)

    for (p_f, p_t), v in data_counter.items():
        if p_t.startswith('type.'):
            xsankey_data_sets['dir-to-line'].add(p_f)
            #xsankey_data_cntr[p_f] += v
            xsankey_data_line[p_f].add(p_t)
        else:
            xsankey_data_sets['dir-to-dir'].add(p_f)

    xsankey_data_sets['intersection'] = xsankey_data_sets['dir-to-dir'] & xsankey_data_sets['dir-to-line']

    #xsankey_data_extracted = {k: v for k, v in xsankey_data_cntr.items() if k in xsankey_data_sets['intersection']}

    for d in xsankey_data_sets['intersection']:
        #print(f"{d!r}:")
        for l in xsankey_data_line[d]:
            #print(f"    {l!r}")
            res[(f"__{d}__", l)]  = res[(d, l)]
            res[(d, f"__{d}__")] += res[(d, l)]
            del res[(d, l)]

    return res


def reduce_sankey_from_tail(data_counter: Counter) -> Counter:
    res = data_counter.copy()

    #print("reduce_sankey_from_tail():")

    max_level = 0
    for (p_f, _) in data_counter.keys():
        n_dashes = p_f.count('/')
        if n_dashes > max_level:
            max_level = n_dashes

    #print(f"  {max_level=}")

    to_delete = lambda x: x.count('/') == max_level
    can_delete = True

    helper_info = {
        'delete-contents': defaultdict(dict),
        'to-prev': {}
    }

    # sanity check
    for k, v in data_counter.items():
        (p_f, p_t) = k
        if to_delete(p_f):
            if not p_t.startswith('type.'):
                #print(f"  {p_f!r} is not final: {p_f!r} =[{v}]=> {p_t!r}")
                can_delete = False
            else:
                helper_info['delete-contents'][p_f][p_t] = v

        if to_delete(p_t):
            helper_info['to-prev'][p_t] = p_f

    #print(f"  {can_delete=}")

    if can_delete:
        to_prev_dict = {}
        for p_t, p_f in helper_info['to-prev'].items():
            if (p_f, f"__{p_f}__") in data_counter:
                #print(f"({p_f}, __{p_f}__): {xsankey_cntr_5[(p_f, f'__{p_f}__')]}")
                to_prev_dict[f"__{p_f}__"] = p_f

        #print(f"  extra 'to-prev':{len(to_prev_dict)}")
        helper_info['to-prev'] |= to_prev_dict

        for k, v in data_counter.items():
            (p_f, p_t) = k
            if (p_f in helper_info['to-prev'] and
                p_t.startswith('type.')):
                helper_info['delete-contents'][p_f][p_t] = v

        for k, v in data_counter.items():  # we are changing res
            (p_f, p_t) = k
            if p_t in helper_info['to-prev'] and p_f == helper_info['to-prev'][p_t]:
                #print(f"({p_f}, {p_t}): {v})")
                for kk, vv in helper_info['delete-contents'][p_t].items():
                    res[(p_f, kk)] += vv
                    #print(f"  ({p_f}, {kk}) += {vv} => {res[(p_f, kk)]}")
                del res[(p_f, p_t)]
            if p_f in helper_info['to-prev']:
                del res[(p_f, p_t)]

    return res


def reduce_sankey_thin_out(data_counter: Counter,
                           threshold_ratio: float = 0.005) -> Counter:
    #print("reduce_sankey_thin_out():")
    # TODO: use threshold on max value, not on sum of values

    total_lines = 0  #: total changed lines in whole project
    for (p_f, p_t), v in data_counter.items():
        if p_f != '.':
            continue
        total_lines += v

    #print(f"  {total_lines=}")
    #print(f"  threshold={threshold_ratio}*{total_lines}={threshold_ratio * total_lines}")

    data_info = {
        'to-remove': set()
    }

    for (p_f, p_t), v in data_counter.items():
        if v < threshold_ratio * total_lines:
            #print(f"  - ({p_f}, {p_t}): {v} {'*' if p_t.startswith('type.') else ' '}")
            data_info['to-remove'].add(p_f)

    data_info |= {
        'delete-contents': defaultdict(dict),
        'to-prev': {},
        'can-remove': set(),
    }

    #print("  gathering data:")

    for (p_f, p_t), v in data_counter.items():
        # want to remove, and can remove
        if p_f in data_info['to-remove'] and p_t.startswith('type.'):
            #print(f"   - saving data for ({p_f}, {p_t}): {v}")
            data_info['delete-contents'][p_f][p_t] = v

    for (p_f, p_t), v in data_counter.items():
        if p_t in data_info['to-remove'] and p_t in data_info['delete-contents']:
            data_info['to-prev'][p_t] = p_f

            total_width = 0
            for v in data_info['delete-contents'][p_t].values():
                total_width += v
            if total_width < threshold_ratio * total_lines:
                if f"__{p_f}__" == p_t:
                    #print(f"   ! ({p_f}) -> ({p_t}) -> {data_info['delete-contents'][p_t]}")
                    pass
                elif p_f == ".":
                    #print(f"   # ({p_f}) -> ({p_t}) -> {data_info['delete-contents'][p_t]}")
                    pass
                else:
                    #print(f"   + ({p_f}) => ({p_t}) => {data_info['delete-contents'][p_t]}")
                    data_info['can-remove'].add(p_t)
            else:
                #print(f"  - ({p_f}) -> ({p_t}) -> {data_info['delete-contents'][p_t]}")
                pass

    ## -------------------------------------------------------
    ## actual removal
    res = data_counter.copy()

    #print("  deleting/compressing:")
    for k, v in data_counter.items():  # we are changing res
        (p_f, p_t) = k
        if p_t in data_info['can-remove']:
            if p_t in data_info['to-prev'] and p_f == data_info['to-prev'][p_t]:
                #print(f"  - ({p_f}, {p_t}): {v})")
                for kk, vv in data_info['delete-contents'][p_t].items():
                    res[(p_f, kk)] += vv
                    #print(f"  ({p_f}, {kk}) += {vv} => {res[(p_f, kk)]}")
                del res[(p_f, p_t)]

        if p_f in data_info['can-remove']:
            if p_f in data_info['to-prev']:
                del res[(p_f, p_t)]

    return res


def sankey_df_from_triples(data_list: list[tuple[str, str, int]]) -> pd.DataFrame:
    df = pd.DataFrame.from_records(data_list, columns=['source', 'target', 'count'])

    df['from'] = df['source'] \
        .str.replace(r'^\.$', '{qtile}', regex=True)
    df['to'] = df['target'] \
        .str.replace(r'^type\.(.*)$', lambda m: f"[{m.group(1)}]", regex=True)

    return df


def process_sankey(lines_stats_counter: Optional[Counter],
                   max_files: Optional[int] = None,
                   threshold: float = 0.0) -> Optional[pd.DataFrame]:
    if lines_stats_counter is None:
        return None

    changed_files = sorted_changed_files(lines_stats_counter=lines_stats_counter)
    if max_files is not None:
        lines_stats_counter = limit_count_to_selected_files(
            lines_stats_counter=lines_stats_counter,
            files=changed_files[:max_files]
        )

    sankey_counter = path_to_dirs_only_counter(lines_stats_counter)
    sankey_counter = add_dashdash_dirs_to_counter(sankey_counter)
    if 0.0 < threshold < 1.0:
        sankey_counter = reduce_sankey_thin_out(sankey_counter, threshold_ratio=threshold)

    sankey_triples = sankey_triples_from_counter(sankey_counter)
    sankey_df = sankey_df_from_triples(sankey_triples)

    return sankey_df


class LinesStatsDataStore(pn.viewable.Viewer):
    dataset_dir = param.Foldername(
        constant=True,
        doc="Dataset directory with *.lines-stats.*.json files "
            "(used if `timeseries_file_path` is relative path)",
    )
    timeseries_file = param.String(
        allow_refs=True,  # to allow widgets and reactive expressions
        doc="Selected JSON file with timeline data to find lines-stats companion for"
    )
    repo_name = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Name of the repository, for selecting data",
    )
    disable_widgets = param.Boolean(
        default=False,
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Whether to disable widgets controlling construction of Sankey diagram"
    )

    def __init__(self, **params):
        super().__init__(**params)

        self.lines_stats_data_rx = pn.rx(get_lines_stats_data)(
            dataset_dir=self.dataset_dir,  # does not change, no need for rx
            timeseries_file=self.param.timeseries_file.rx(),
        )
        self.lines_stats_counter_rx = pn.rx(count_file_x_line_in_lines_stats)(
            lines_stats_data=self.lines_stats_data_rx,
            repo_name=self.param.repo_name.rx(),
        )

        self.num_files_widget = pn.widgets.Select(
            name="top N files",
            options=[10,100,None],
            value=100,
        )
        self.sankey_df_rx = pn.rx(process_sankey)(
            lines_stats_counter=self.lines_stats_counter_rx,
            max_files=self.num_files_widget,
        )

        self._widgets = [
            self.num_files_widget,
        ]

    def __panel__(self) -> pn.viewable.Viewable:
        return pn.WidgetBox(  # column
            'Sankey diagram',
            *self._widgets,
            disabled=self.disable_widgets,
        )
