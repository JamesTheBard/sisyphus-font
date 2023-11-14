import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Union

from loguru import logger


class StyleFields(Enum):
    """Style field breakdown (v4) for the SSA content.
    """
    STYLE_NAME = 0
    FAMILY = 1
    SUBFAMILY_BOLD = 7
    SUBFAMILY_ITALIC = 8


@dataclass
class SubFont:
    """Subtitle font found in the SSA content.

    Attributes:
        style (str): The style associated with the font if found in the style section, otherwise the line of dialogue.
        family (str): The font family/name.
        subfamily (list[str]): The subfamily of the font, usually a combination of 'bold', 'italic', or 'regular' as a list.
    """
    style: str
    family: str
    subfamily: list[str]


class SubParse:
    """Parse a SubStation Alpha subtitle file for all used fonts.

    Attributes:
        content (list[str]): The content of the subtitle file.
        ssa_file (Path): The Path to the subtitle file.
        styles (list[SubFont]): A list of all SubFonts found in the subtitles.
    """

    ssa_file: Path
    content: list[str]
    _styles: list[SubFont]
    _dialogue: list[SubFont]

    def __init__(self, ssa_file: Union[Path, str]):
        """Initialize the SubParse object.

        Args:
            ssa_file (Union[Path, str]): The path to the subtitle file.

        Raises:
            FileNotFoundError: The file specified was not found.
            PermissionError: Not allowed to open the specified file.
        """
        self.ssa_file = Path(ssa_file)
        self.content = self.get_content()
        self._styles = self.process_style_section()
        self._dialogue = self.process_dialogue_section()

    def get_content(self) -> list[str]:
        """Load all of the content of the SSA file to memory for parsing.

        Returns:
            list[str]: A list of strings (all the subtitle content)

        Raises:
            FileNotFoundError: The file specified was not found.
            PermissionError: Not allowed to open the specified file.
        """
        with self.ssa_file.open('r', encoding="utf-8") as f:
            return f.readlines()

    def process_style_section(self) -> list[SubFont]:
        """Process the Style v4 section of the subtitles.

        Returns:
            list[SubFont]: A list of all the found fonts in the Style v4 section.
        """
        content = [i for i in self.content if i.startswith('Style: ')]
        results = list()
        for c in content:
            c = c.split(':')[1].split(',')
            style = c[StyleFields.STYLE_NAME.value]
            family = c[StyleFields.FAMILY.value]
            subfamily = list()
            if c[StyleFields.SUBFAMILY_BOLD.value] == "-1":
                subfamily.append("bold")
            if c[StyleFields.SUBFAMILY_ITALIC.value] == "-1":
                subfamily.append("italic")
            results.append(SubFont(style.strip(), family, subfamily))

        dialogue = [i for i in self.content if i.startswith('Dialogue: ')]
        new_results = list()
        for r in results:
            found_result = False
            for d in dialogue:
                style = d.split(',')[3].strip()
                if style == r.style:
                    new_results.append(r)
                    found_result = True
                    break
            if not found_result:
                logger.debug(
                    f"Removing style '{r.style}': not referenced in dialogue.")
        return new_results

    def process_dialogue_section(self) -> list[SubFont]:
        """Process all dialog for font family/subfamily tags.

        Returns:
            list[SubFont]: A list of all the fonts found in the dialogue section.
        """
        content = [i for i in self.content if i.startswith('Dialogue: ')]
        results = list()
        for idx, c in enumerate(content):
            dialogue = ''.join(c.split(',')[9:])
            style = [i for i in self._styles if i.style == c.split(',')[3]][0]
            family, subfamilies, not_subfamilies = None, list(), list()
            if (font_name := re.search(r'\\fn(.+?)(?:[}\\])', dialogue)):
                family = font_name.group(1)
            if (bold := re.search(r'\\b(\d+)(?:[}\\])', dialogue)):
                if int(bold.group(1)) == 0:
                    not_subfamilies.append("bold")
                else:
                    subfamilies.append("bold")
            if (italic := re.search(r'\\i(\d)(?:[}\\])', dialogue)):
                if int(italic.group(1)) == 0:
                    not_subfamilies.append("italic")
                else:
                    subfamilies.append("italic")
            if family or subfamilies or not_subfamilies:
                if not family:
                    family = style.family
                    if subfamilies:
                        subfamilies = list(
                            set(subfamilies).union(style.subfamily))
                    else:
                        subfamilies = list(
                            set(subfamilies).difference(not_subfamilies))
                results.append(
                    SubFont(f"dialogue:{idx:05}", family, subfamilies))
        return results

    @property
    def styles(self) -> list[SubFont]:
        """A list of all found styles.

        Returns:
            list[SubFont]: A list of all found font information in the SSA file.
        """
        return self._styles + self._dialogue
