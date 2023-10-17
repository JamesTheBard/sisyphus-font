from pathlib import Path
from dataclasses import dataclass
from typing import Union
from loguru import logger
from fuzzywuzzy import fuzz
from typing import List, Optional
from fontTools import ttLib


@dataclass
class Font:
    family: Optional[str] = None
    subfamily: Optional[list] = None
    full_name: Optional[str] = None
    font_path: Optional[str] = None


@dataclass
class FontResult:
    font: Font
    family_match_score: int
    subfamily_match_score: int

    def _total_score(self, other):
        self_score = self.family_match_score * 1000 + self.subfamily_match_score
        other_score = other.family_match_score * 1000 + other.subfamily_match_score
        return (self_score, other_score)

    def __eq__(self, other):
        s, o = self._total_score(other)
        return s == o

    def __ne__(self, other):
        s, o = self._total_score(other)
        return s != o

    def __lt__(self, other):
        s, o = self._total_score(other)
        return s < o

    def __le__(self, other):
        s, o = self._total_score(other)
        return s <= o

    def __gt__(self, other):
        s, o = self._total_score(other)
        return s > o

    def __ge__(self, other):
        s, o = self._total_score(other)
        return s >= o


class FontLibrary:

    library: List[Font]

    def __init__(self, library_path: Union[Path, str]):
        self.library_path = Path(library_path)
        self.library = self.parse_library()

    def parse_library(self) -> List[Font]:
        results = list()
        for f in self.library_path.glob("*"):
            if f.suffix.lower() not in [".ttf", ".otf"]:
                continue
            ttf = ttLib.TTFont(f)['name']
            font = Font()
            font.family = ttf.getBestFamilyName()
            font.subfamily = sorted(
                [i.lower() for i in ttf.getBestSubFamilyName().split(" ")])
            font.full_name = ttf.getBestFullName()
            font.font_path = f
            results.append(font)
        return results

    def find_font(self, family: str, subfamily: Union[list[str], str], ignore_regular: bool = False, use_full_name: bool = False, threshold: int = 80) -> FontResult:
        if isinstance(subfamily, str):
            subfamily = [subfamily.split(" ")]
        subfamily = [i.lower() for i in subfamily]
        results = list()

        if not use_full_name:
            if ignore_regular:
                subfamily = [i for i in subfamily if i not in ["bold", "italic"]]
            subfamily = ' '.join(subfamily)
            for font in self.library:
                if ignore_regular:
                    sfam = [i for i in font.subfamily if i not in ["bold", "italic"]]
                sfam = ' '.join(sfam)
                family_score = fuzz.ratio(family, font.family)
                subfamily_score = fuzz.ratio(subfamily, sfam)

                if family_score >= threshold:
                    results.append(FontResult(font, family_score, subfamily_score))

        else:
            for font in self.library:
                sfmt = ' '.join(i.capitalize() for i in subfamily)
                full_name = f"{family} {sfmt}"
                family_score = fuzz.ratio(full_name.lower(), font.full_name.lower())
                if family_score >= threshold:
                    results.append(FontResult(font, family_score, 100))

        try:
            return sorted(results)[-1]
        except IndexError:
            return None

    def find_font_by_family(self, family: str, threshold: int = 80) -> List[FontResult]:
        f_attrs = ["font", "preferred"]
        results = list()
        for font in self.library:
            family_score = fuzz.ratio(family, font.family)
            if family_score >= threshold:
                results.append(FontResult(font, family_score, 0))
        return sorted(results, reverse=True)
