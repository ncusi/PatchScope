import logging
import re
from pathlib import PurePath

import mkdocs.plugins

log = logging.getLogger('mkdocs')

@mkdocs.plugins.event_priority(-50)
def on_page_markdown(markdown, page, **kwargs):
    path = page.file.src_uri
    changed = 0

    def replace_links(match_obj):
        nonlocal changed

        include_markdown_reversed = {
            '../README.md': 'index.md',
            '../data/examples/README.md': 'examples.md',
            '../notebooks/README.md': 'notebooks.md',
            '../notebooks/panel/README.md': 'notebooks.md',
            '../schema/README.md': 'schema.md',
            '../src/diffinsights_web/README.md': 'diffinsights_web.md',
        }
        fragment: str = ''

        if match_obj.group('hash') is not None:
            fragment = match_obj.group('hash')

        if match_obj.group('link') and match_obj.group('link').startswith('https://'):
            # external link
            #log.info(f"- external link => {match_obj.group('link')}{fragment}")
            return match_obj.group(0)  # whole match
        elif not match_obj.group('link') and match_obj.group('hash'):
            # internal link
            #log.info(f"- internal link => {match_obj.group('hash')}")
            return match_obj.group(0)  # whole match

        orig_link = match_obj.group('link')
        try:
            rebased_link = PurePath(orig_link).relative_to(PurePath(path))
        except ValueError:
            rebased_link = orig_link

        if rebased_link.startswith('../'):
            if rebased_link in include_markdown_reversed:
                replacement_link = f"{include_markdown_reversed[rebased_link]}{fragment}"
            else:
                replacement_link = f"https://github.com/ncusi/PatchScope/blob/main/{rebased_link[3:]}{fragment}"

            #log.info(f"- inner link => {rebased_link}{match_obj.group('hash') or ''} replaced with {replacement_link}")
            changed += 1
            return f"[{match_obj.group('src')}]({replacement_link})"
        #else:
        #    log.info(f"- inner link in {path} => {orig_link} -> {rebased_link}")

        return match_obj.group(0)

    if path.startswith('api_reference/') or path.startswith('cli_reference/'):
        return None
    if path.endswith('/SUMMARY.md'):
        return None

    #log.info(f"Processing documentation file '{path}'")

    for m in re.finditer(r'\bhttp://[^)> ]+', markdown):
        log.warning(f"Documentation file '{path}' contains a non-HTTPS link: {m[0]}")

    replacement = re.sub(
        pattern=r'\[(?P<src>.*?)\]\((?P<link>.*?)(?P<hash>#[^)]*)?\)',
        repl=replace_links,
        string=markdown,
    )

    if changed:
        log.info(f"Rewrote {changed:2d} link(s) in documentation file '{path}'")
        return replacement
    elif replacement != markdown:  # just in case
        log.info(f"CHANGED contents of documentation file '{path}'")
        return replacement
    else:
        return None
