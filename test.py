from fontscrape.subparse import SubParse
from fontscrape.fonts import FontLibrary

a = SubParse('test4.ssa')
sub_fonts = a.process_style_section()
a.process_dialogue_section()

# f = FontLibrary('fonts2')
# for i in sub_fonts:
#     print(f.find_font(i.family, i.subfamily, use_full_name=True, ignore_regular=True))