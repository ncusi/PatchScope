from enum import Enum

import panel as pn
import param

from diffinsights_web.datastore.timeline import TimelineDataStore


class TimelineView(pn.viewable.Viewer):
    """Base class for different views that display data from TimelineDataStore"""
    data_store = param.ClassSelector(class_=TimelineDataStore)

    def __init__(self, **params):
        super().__init__(**params)


class SpecialColumnEnum(Enum):
    LINE_TYPES_PERC = "timeline|KIND [%]"
    SANKEY_DIAGRAM = "sankey|SANKEY"
    NO_PLOT = "<NO PLOT>"


#: for the ContributorsHeader.select_contribution_type_widget
contribution_types_map = {
    "Commits": "timeline|n_commits",
    "Additions": "timeline|+:count",
    "Deletions": "timeline|-:count",
    "Files changed": "timeline|file_names",
    "Patch size (lines)": "timeline|diff.patch_size",
    "Patch spreading (lines)": "timeline|diff.groups_spread",
    # special cases:
    "Line types distribution [%]": SpecialColumnEnum.LINE_TYPES_PERC.value,
    "Flow from path to line type": SpecialColumnEnum.SANKEY_DIAGRAM.value,
    "No plot": SpecialColumnEnum.NO_PLOT.value  # this special value should be last
}
column_to_contribution = {
    v: k for k, v in contribution_types_map.items()
}
