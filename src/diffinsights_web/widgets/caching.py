import panel as pn


class ClearCacheButton(pn.viewable.Viewer):
    def __init__(self, **params):
        super().__init__(**params)

        self.clear_button = pn.widgets.Button(
            name="Clear cache",
            button_type="danger",
        )
        self.clear_button.on_click(lambda _events: pn.state.clear_caches()),

    def __panel__(self):
        return self.clear_button
