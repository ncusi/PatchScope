import panel as pn


# TODO: replace with a better mechanism, e.g. Proxy object for pn.state.notifications
warnings_list: list[str] = []
# NOTE: you need to set it to False in the app, in order for it to work
loaded = False

pn.config.notifications = True  # just in case the app did not set it


def warning_notification(msg: str) -> None:
    if loaded:
        if pn.state.notifications is not None:
            pn.state.notifications.warning(msg)
    else:
        warnings_list.append(msg)


def onload_callback() -> None:
    global loaded

    if pn.state.notifications is not None:
        for warning in warnings_list:
            pn.state.notifications.warning(warning)

    warnings_list.clear()
    loaded = True  # NOTE: without global would create local variable
