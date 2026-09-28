import sys, importlib
from pixlib import sheet, preview
mod = importlib.import_module(sys.argv[1])
rows = [fn() for (_, fn, _, _) in mod.ANIMS]
img = sheet(rows, 48, 48)
preview(img, int(sys.argv[2]) if len(sys.argv) > 2 else 5).save(sys.argv[3] if len(sys.argv) > 3 else '/tmp/claude-0/-home-claude/2029e11c-6559-530b-a3f4-f05a1c6e48b1/scratchpad/prev.png')
