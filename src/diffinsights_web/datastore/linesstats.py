import json
from collections import Counter
from collections.abc import Container, Iterable
from pathlib import Path
from typing import Union, Optional

import panel as pn
import param

from diffinsights_web.utils.notifications import warning_notification


def get_lines_stats_data(dataset_dir: str, timeseries_file: str) -> Optional[dict]:
    timeseries_file_path = Path(timeseries_file)
    if not timeseries_file_path.is_absolute():
        timeseries_file_path = Path(dataset_dir).joinpath(timeseries_file)

    dataset_dir = timeseries_file_path.parent
    lines_stats_file = timeseries_file_path.name.replace('.timeline.', '.lines-stats.')
    file_path = dataset_dir.joinpath(lines_stats_file)

    if file_path.is_file():
        with open(file_path, mode='r') as json_fp:
            return json.load(json_fp)
    else:
        return None


def count_file_x_line_in_lines_stats(lines_stats_data: dict,
                                     repo_name: str,
                                     change_type: str = "+/-",
                                     prefix: str = 'type.') -> Counter:
    #print(f"count_file_line_in_lines_stats(..., {repo_name=}, {change_type=}, {prefix=})")
    result = Counter()

    for dataset, dataset_data in lines_stats_data.items():
        for bug_or_repo, lines_data in dataset_data.items():
            if bug_or_repo != repo_name:
                print(f"    - skipping: {bug_or_repo!r} != {repo_name!r}")

            for patch_file, patch_data in lines_data.items():
                for file_name, file_data in patch_data.items():
                    if change_type not in file_data:
                        continue

                    for line_info, n_lines in file_data[change_type].items():
                        if not line_info.startswith(prefix):
                            continue

                        result[(file_name, line_info)] += n_lines

    return result


def sorted_changed_files(lines_stats_counter: Counter) -> list[str]:
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

    def __init__(self, **params):
        super().__init__(**params)

        self.lines_stats_data_rx = pn.rx(get_lines_stats_data)(
            dataset_dir=self.dataset_dir,
            timeseries_file=self.timeseries_file,
        )
        self.lines_stats_counter_rx = pn.rx(count_file_x_line_in_lines_stats)(
            lines_stats_data=self.lines_stats_data_rx,
            repo_name=self.repo_name,
        )

