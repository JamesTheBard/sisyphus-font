from pathlib import Path
import sys

from loguru import logger

from fontscrape.fonts import FontLibrary
from fontscrape.subparse import SubParse

# Load all of the fonts in the 'fonts' directory and process them.  The results
# will end up in the font_library.library attribute.
font_library = FontLibrary('fonts')
# [print(font) for font in font_library.library]


fonts = list()
subs = Path('.').glob("*.ssa")
for sub in subs:
    logger.info(f"Processing subtitle file: {sub}")

    # Load the subtitles file, parse all of the 'style' and 'dialogue' information for
    # font definitions and tags, then make them accessible via the 'sub_fonts.styles'
    # method.
    try:
        sub_fonts = SubParse(sub)
    except FileNotFoundError:
        logger.critical(f"File does not exist: {str(sub.absolute())}")
        sys.exit(2)
    except PermissionError:
        logger.critical(f"Cannot open the file: {str(sub.absolute())}")
        sys.exit(3)
    # [print(style) for style in sub_fonts.styles]

    # Compare the styles found in the subtitle file with fonts in the library and
    # return the fonts that match the best.  The threshold is set to 90% which seems
    # to work best for identifying fonts.  If a font can't be found, there will be
    # a warning in the logs.
    for style in sub_fonts.styles:
        fonts.append(
            font_library.find_font_by_full_name(
                family=style.family,
                subfamily=style.subfamily,
                downgrade=True
            )
        )

# Remove all duplicate fonts and return the fonts found.
fonts = set([i.font for i in fonts if i])
[logger.info(f"Found font: {i.font_path}") for i in fonts]
