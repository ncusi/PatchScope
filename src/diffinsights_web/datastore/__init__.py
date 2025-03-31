from pathlib import Path
from typing import Optional

import panel as pn

DATASET_DIR = 'data/examples/stats'
default_repo = 'qtile'  # NOTE: used if available


@pn.cache
def find_dataset_dir() -> Optional[Path]:
    for TOP_DIR in ['', '..', '../..']:
        full_dir = Path(TOP_DIR).joinpath(DATASET_DIR)

        if full_dir.is_dir():
            return full_dir

    return None
