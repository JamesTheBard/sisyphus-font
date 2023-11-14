from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from fontTools import ttLib
from fuzzywuzzy import fuzz
from loguru import logger


@dataclass
class Font:
    """A Font object containing all the information for a processed font.

    Attributes:
        family (str): The font family.
        subfamily (list[str]): The font subfamily.
        full_name (str): The full name of the font.
        font_path (Path): The filesystem location of the font.
    """
    family: str
    subfamily: list[str]
    full_name: str
    font_path: Path

    def __eq__(self, other):
        return self.full_path == other.full_path

    def __hash__(self):
        return hash(self.full_name)


@dataclass
class FontResult:
    """The result of a font comparison.

    FontResults can be compared against each other, where the `family_match_score` is compared first, then the `subfamily_match_score` afterwards.

    Attributes:
        font (Font): The Font that matched.
        family_match_score (int): The 'confidence' of the family match. Range is from 0 to 100.
        subfamily_match_score (int): The 'confidence' of the subfamily match. Range is from 0 to 100.
        downgrade (bool): Whether the font was downgraded during the matching process.
    """
    font: Font
    family_match_score: int
    subfamily_match_score: int
    downgrade: bool = False

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
    """Create a font library from a given directory of fonts.

    Attributes:
        library (list[Font]): A list of Fonts containing font information from the fonts in the library path.
        library_path (Union[Path, str]): The path of the directory containing the fonts to parse.
    """

    library: list[Font]
    library_path: Union[Path, str]

    def __init__(self, library_path: Union[Path, str]):
        """Create the font library.

        Args:
            library_path (Union[Path, str]): The path of the directory containing the fonts to parse.
        """
        self.library_path = Path(library_path)
        self.library = self.parse_library()

    def parse_library(self) -> list[Font]:
        """Parse all of the fonts in the library."""
        results = list()
        for f in self.library_path.glob("*"):
            if f.suffix.lower() not in [".ttf", ".otf"]:
                continue
            ttf = ttLib.TTFont(f)['name']
            font = Font(
                family=ttf.getBestFamilyName(),
                subfamily=sorted([i.lower() for i in ttf.getBestSubFamilyName().split(" ")]),
                full_name=ttf.getBestFullName(),
                font_path=f
            )
            results.append(font)
        return results

    def find_font_by_families(self, family: str,
                              subfamily: Union[list[str], str],
                              ignore_regular: bool = False,
                              downgrade: bool = False,
                              threshold: int = 90) -> Optional[FontResult]:
        """Find a font using a specific family and subfamily comparison.

        Args:
            family (str): The font family.
            subfamily (Union[list[str]], str]): The font subfamily.
            ignore_regular (bool, optional): Ignore the 'regular' subfamily when doing comparisons. Defaults to False.
            downgrade (bool, optional): Allow the font to downgrade to the base font sans subfamily. Defaults to False.
            threshold (int, optional): The threshold to match against. Defaults to 90.

        Returns:
            Optional[FontResult]: The FontResult match if it meets/exceeds the threshold, otherwise None.
        """
        orig_subfamily = subfamily
        if isinstance(subfamily, str):
            subfamily = [subfamily.split(" ")]
        sfam = [i.lower() for i in subfamily]
        results = list()

        if ignore_regular:
            subfamily = [i for i in subfamily if i not in ["bold", "italic"]]
            subfamily = ' '.join(subfamily)
            for font in self.library:
                sfam = subfamily
                if ignore_regular:
                    sfam = [i for i in font.subfamily if i not in [
                        "bold", "italic"]]
                sfam = ' '.join(sfam)
                family_score = fuzz.ratio(family, font.family)
                subfamily_score = fuzz.ratio(subfamily, sfam)

                if family_score >= threshold:
                    results.append(FontResult(
                        font, family_score, subfamily_score))
            if not results and downgrade:
                sfam = ' '.join(sfam)
                family_score = fuzz.ratio(family, font.family)

                if family_score >= threshold:
                    results.append(FontResult(
                        font, family_score, subfamily_score, True))

            try:
                results = sorted(results)[-1]
            except IndexError:
                results = None

            if not results:
                subfamily = ', '.join(subfamily) if subfamily else "None"
                logger.warning(
                    f"Could not find font: {family}, subfamilies: {orig_subfamily}")
                return results

            font = results.font
            dg_flag = "↓" if results.downgrade else " "
            subfamily = ', '.join(font.subfamily) if subfamily else "None"
            logger.debug(
                f"Found font: [{dg_flag}{results.family_match_score:>3}%] {font.family}, subfamilies: {subfamily}")
            return results

    def find_font_by_full_name(self, family: str,
                               subfamily: Union[list[str], str],
                               downgrade: bool = False,
                               threshold: int = 90) -> Optional[FontResult]:
        """Find a font by comparing the family/subfamily to the font's full name.

        Args:
            family (str): The font family.
            subfamily (Union[list[str], str]): The font subfamily.
            downgrade (bool, optional): Allow the font to downgrade to the base font sans subfamily. Defaults to False.
            threshold (int, optional): The threshold to match against. Defaults to 90.

        Returns:
            Optional[FontResult]: The FontResult match if it meets/exceeds the threshold, otherwise None.
        """
        orig_subfamily = subfamily
        if isinstance(subfamily, str):
            subfamily = [subfamily.split(" ")]
        results = list()
        for font in self.library:
            sfmt = ' '.join(i.capitalize() for i in subfamily)
            full_name = f"{family} {sfmt}"
            family_score = fuzz.ratio(
                full_name.lower(), font.full_name.lower()
            )
            if family_score >= threshold:
                results.append(FontResult(font, family_score, 0))
        if not results:
            for font in self.library:
                ffull_name = ' '.join([i.replace("semi", "") for i in [
                                      j for j in font.full_name.lower().split(" ")]])
                sfmt = ' '.join(i.capitalize() for i in subfamily)
                full_name = f"{family} {sfmt}"
                family_score = fuzz.ratio(full_name.lower(), ffull_name)
                if family_score >= threshold:
                    results.append(FontResult(font, family_score, 0))
        if not results and downgrade:
            for font in self.library:
                full_name = f"{family}"
                family_score = fuzz.ratio(
                    full_name.lower(), font.full_name.lower())
                if family_score >= threshold:
                    results.append(FontResult(font, family_score, 0, True))

        try:
            results = sorted(results)[-1]
        except IndexError:
            results = None

        if not results:
            subfamily = ', '.join(subfamily) if subfamily else "None"
            logger.warning(
                f"Could not find font: {family}, subfamilies: {orig_subfamily}")
        else:
            font = results.font
            dg_flag = "↓" if results.downgrade else " "
            subfamily = ', '.join(font.subfamily) if subfamily else "None"
            logger.debug(
                f"Found font: [{dg_flag}{results.family_match_score:>3}%] {font.family}, subfamilies: {subfamily}")
        return results

    def find_font_by_family(self, family: str, threshold: int = 90) -> list[FontResult]:
        """Find a font by only comparing against the font family.

        Args:
            family (str): The font family.
            threshold (int, optional): The threshold to match against. Defaults to 90.

        Returns:
            List[FontResult]: A list of FontResult matches that meet/exceed the threshold sorted by confidence (decending).
        """
        results = list()
        for font in self.library:
            family_score = fuzz.ratio(family, font.family)
            if family_score >= threshold:
                results.append(FontResult(font, family_score, 0))
        return sorted(results, reverse=True)
