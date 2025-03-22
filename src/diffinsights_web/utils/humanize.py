"""Provide human-readable value, together with machine-readable HTML metadata/microdata"""
import os

import pandas as pd


def html_date_humane(date: pd.Timestamp) -> str:
    date_format = '%d %b %Y'
    if os.name == 'nt':
        date_format = '%#d %b %Y'
    elif os.name == 'posix':
        date_format = '%-d %b %Y'

    return f'<time datetime="{date.isoformat()}">{date.strftime(date_format)}</time>'


def html_int_humane(val: int) -> str:
    thousands_sep = " "  # Unicode thin space (breakable in HTML), &thinsp;

    res = f'{val:,}'
    if thousands_sep != ",":
        res = res.replace(",", thousands_sep)

    return f'<data value="{val}" style="white-space: nowrap;">{res}</data>'
