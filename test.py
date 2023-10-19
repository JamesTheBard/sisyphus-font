from pathlib import Path

from loguru import logger

from fontscrape.fonts import FontLibrary
from fontscrape.subparse import SubParse

fl = FontLibrary('fonts')

fonts = list()
subs = Path('.').glob("*.ssa")
for sub in subs:
    logger.info(f"Processing subtitle file: {sub}")
    a = SubParse(sub)
    for style in a.styles:
        fonts.append(
            fl.find_font(style.family, style.subfamily,
                         use_full_name=True, downgrade=True, threshold=90)
        )

fonts = set([i.font for i in fonts if i])
[logger.info(f"Found font: {i.font_path}") for i in fonts]
