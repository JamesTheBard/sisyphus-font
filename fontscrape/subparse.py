from typing import Union, List
from pathlib import Path
from enum import Enum
from dataclasses import dataclass
from fontscrape.fonts import FontLibrary
import re


class StyleFields(Enum):
    STYLE_NAME = 0
    FAMILY = 1
    SUBFAMILY_BOLD = 7
    SUBFAMILY_ITALIC = 8


@dataclass
class SubFont:
    style: str
    family: str
    subfamily: list[str]
    

class SubParse:
    def __init__(self, ssa_file: Union[Path, str]):
        self.ssa_file = Path(ssa_file)
        self.content = self.get_content()
        self.styles = self.process_style_section()

    def get_content(self):
        with self.ssa_file.open('r', encoding="utf-8") as f:
            return f.readlines()

    def process_style_section(self) -> List[SubFont]:
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
        return results
    
    def process_dialogue_section(self) -> List[SubFont]:
        content = [i for i in self.content if i.startswith('Dialogue: ')]
        for c in content:
            dialogue = ''.join(c.split(',')[9:])
            style = [i for i in self.styles if i.style == c.split(',')[3]][0]
            family, subfamilies = None, list()
            if (font_name := re.search(r'\\fn(.+?)(?:[}\\])', dialogue)):
                font = font_name.group(1)
            if re.search(r'\\b1(?:[}\\])', dialogue):
                subfamilies.append("bold")
            if re.search(r'\\i1(?:[}\\])', dialogue):
                subfamilies.append("italic")
                
            # print(style)