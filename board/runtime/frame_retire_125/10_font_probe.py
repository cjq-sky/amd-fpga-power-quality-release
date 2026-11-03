"""Read-only installed font coverage check, independent of acquisition/display owner."""
from PIL import ImageFont
from pathlib import Path
import json


def signature(font, char):
    mask=font.getmask(char)
    return mask.size,bytes(mask)


latin=Path('/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf')
chinese=Path('/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf')
lf=ImageFont.truetype(str(latin),24)
cf=ImageFont.truetype(str(chinese),24)
ascii_ok=all(signature(lf,c)!=signature(lf,'\uffff') for c in '0123456789CHLRLIVE.%/-±')
digits=len({signature(lf,c) for c in '0123456789'})
chinese_ok=all(signature(cf,c)!=signature(cf,'\uffff') for c in '电能质量监测有效值')
if not ascii_ok or digits!=10 or not chinese_ok:
    raise RuntimeError('Installed font coverage check failed')
print(json.dumps(dict(event='FONT_COVERAGE_OK',latin=str(latin),chinese=str(chinese),
                      digit_glyph_count=digits,ascii_ok=ascii_ok,chinese_ok=chinese_ok,
                      original_droid_digit_count=len({signature(cf,c) for c in '0123456789'}))))
