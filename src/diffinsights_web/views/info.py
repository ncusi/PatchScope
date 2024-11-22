import panel as pn
import param

from diffinsights_web.datastore.timeline import frequency_names


@pn.cache
def head_info_html(repo_name: str,
                   resample_freq: str,
                   freq_names: dict[str, str]) -> str:
    return f"""
    <h1>Contributors to {repo_name}</h1>
    <p>Contributions per {freq_names.get(resample_freq, 'unknown frequency')} to HEAD, excluding merge commits</p>
    """


class ContributorsHeader(pn.viewable.Viewer):
    repo = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Name of the repository, for documentation purposes only",
    )
    freq = param.String(
        allow_refs=True,  # allow for reactive expressions, and widgets
        doc="Resampling frequency as frequency string, for documentation purposes only",
        # see table at https://pandas.pydata.org/docs/user_guide/timeseries.html#dateoffset-objects
    )

    head_styles = {
        'font-size': 'larger',
    }

    def __init__(self, **params):
        super().__init__(**params)

        self.head_text_rx = pn.rx(head_info_html)(
            repo_name=self.param.repo.rx(),
            resample_freq=self.param.freq.rx(),
            freq_names=frequency_names,
        )

    def __panel__(self):
        return pn.Row(
            pn.pane.HTML(self.head_text_rx, styles=self.head_styles),
            # select_period_from_widget,
            # select_contribution_type_widget,
        )
