r"""Generate a 15 cm / 5 inch PCB ruler with KiCad's Python API (pcbnew).

Run it with the Python bundled with KiCad:
    "C:\Program Files\KiCad\10.0\bin\python.exe" pcb_ruler.py --out pcb_ruler.kicad_pcb --black

Step-by-step tutorial: https://scriptedpcb.com/en/projects/pcb-ruler-python-kicad/
Video walkthrough:     https://youtu.be/3DMbfdIgksg
"""
import argparse

import pcbnew
from pcbnew import Edge_Cuts, F_Cu, F_Mask, F_SilkS, FromMM, PCB_SHAPE, PCB_TEXT, VECTOR2I

X0, Y0, X1, Y1 = 100.0, 100.0, 262.0, 132.0   # board outline, mm
ZERO = 105.0       # x of the 0 mark, shared by both scales
MARGIN = 0.75      # copper-to-edge clearance (DRC wants 0.5 mm + half the tick width)
TICK_W = 0.22


def mm(x, y):
    return VECTOR2I(FromMM(x), FromMM(y))


def shape(board, kind, layer, width):
    s = PCB_SHAPE(board)
    s.SetShape(kind)
    s.SetLayer(layer)
    s.SetWidth(FromMM(width))
    board.Add(s)
    return s


def seg(board, a, b, layer=F_Cu, w=TICK_W):
    s = shape(board, pcbnew.SHAPE_T_SEGMENT, layer, w)
    s.SetStart(mm(*a))
    s.SetEnd(mm(*b))
    return s


def circle(board, c, r, layer=Edge_Cuts, w=0.1):
    s = shape(board, pcbnew.SHAPE_T_CIRCLE, layer, w)
    s.SetCenter(mm(*c))
    s.SetEnd(mm(c[0] + r, c[1]))
    return s


def rect(board, cx, cy, w, h):
    s = shape(board, pcbnew.SHAPE_T_RECTANGLE, F_Cu, 0.05)
    s.SetStart(mm(cx - w / 2, cy - h / 2))
    s.SetEnd(mm(cx + w / 2, cy + h / 2))
    s.SetFilled(True)
    return s


def text(board, s, x, y, size=1.6, bold=False):
    t = PCB_TEXT(board)
    t.SetText(s)
    t.SetPosition(mm(x, y))
    t.SetLayer(F_SilkS)
    t.SetTextSize(VECTOR2I(FromMM(size), FromMM(size)))
    t.SetTextThickness(FromMM(size * (0.2 if bold else 0.15)))
    board.Add(t)


def outline(board, r=3.0):
    for a, b in (((X0 + r, Y0), (X1 - r, Y0)), ((X1, Y0 + r), (X1, Y1 - r)),
                 ((X1 - r, Y1), (X0 + r, Y1)), ((X0, Y1 - r), (X0, Y0 + r))):
        seg(board, a, b, Edge_Cuts, 0.1)
    for c, start in (((X0 + r, Y0 + r), (X0, Y0 + r)), ((X1 - r, Y0 + r), (X1 - r, Y0)),
                     ((X1 - r, Y1 - r), (X1, Y1 - r)), ((X0 + r, Y1 - r), (X0 + r, Y1))):
        a = shape(board, pcbnew.SHAPE_T_ARC, Edge_Cuts, 0.1)
        a.SetCenter(mm(*c))
        a.SetStart(mm(*start))
        a.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
    circle(board, (X1 - 6, (Y0 + Y1) / 2), 2.5)        # hanging hole


def metric_scale(board):
    for i in range(151):                                   # one tick per mm, 0 to 15 cm
        ln = 4.5 if i % 10 == 0 else 3.0 if i % 5 == 0 else 1.8
        seg(board, (ZERO + i, Y0 + MARGIN), (ZERO + i, Y0 + MARGIN + ln))
    for c in range(16):
        text(board, str(c), ZERO + 10 * c, Y0 + 6.9, 1.7)
    text(board, "cm", ZERO + 154, Y0 + 6.9, 1.4)


def inch_scale(board):
    for i in range(5 * 16 + 1):                            # 1/16 inch ticks, 0 to 5 in
        ln = 4.5 if i % 16 == 0 else 3.2 if i % 8 == 0 else 2.4 if i % 4 == 0 else 1.7 if i % 2 == 0 else 1.1
        x = ZERO + i * 25.4 / 16
        seg(board, (x, Y1 - MARGIN), (x, Y1 - MARGIN - ln))
    for n in range(6):
        text(board, str(n), ZERO + 25.4 * n, Y1 - 6.9, 1.7)
    text(board, "inch", ZERO + 25.4 * 5 + 6, Y1 - 6.9, 1.4)


def gauges(board, ym=(Y0 + Y1) / 2):
    x = 108.0
    for name, w, h in [("0201", 0.6, 0.3), ("0402", 1.0, 0.5), ("0603", 1.6, 0.8),
                       ("0805", 2.0, 1.25), ("1206", 3.2, 1.6), ("2512", 6.3, 3.2)]:
        rect(board, x + w / 2, ym - 0.6, w, h)             # actual SMD body size
        text(board, name, x + w / 2, ym + 2.4, 1.0)
        x += max(w, 4.0) + 2.6
    x = 166.0
    for d in [0.5, 0.8, 1.0, 1.5, 2.0, 3.0]:
        c = (x + d / 2, ym - 0.6)
        circle(board, c, d / 2)                            # real hole (Edge.Cuts)
        circle(board, c, d / 2 + 0.85, F_Cu, 0.6)          # copper ring, 0.55 mm from the hole
        text(board, f"{d:g}", c[0], max(ym + 2.4, c[1] + d / 2 + 2.35), 1.0)
        x += d + 4.2
    text(board, "ScriptedPCB", 228.0, ym - 1.2, 2.2, bold=True)
    text(board, "drawn with Python", 228.0, ym + 1.9, 1.1)


def expose_copper(board):
    """Same shapes on F.Mask: no solder mask over the copper, so it comes out gold (ENIG)."""
    for s in list(board.GetDrawings()):
        if isinstance(s, PCB_SHAPE) and s.GetLayer() == F_Cu:
            m = s.Duplicate()
            m.SetLayer(F_Mask)
            m.SetWidth(s.GetWidth() + FromMM(0.08))
            board.Add(m)


# Black solder mask + white silkscreen + ENIG, so the 3D view and the fab order match the photo.
# The stackup is not exposed to the Python API, so it is written into the saved file.
BLACK_STACKUP = """(setup
		(stackup
			(layer "F.SilkS" (type "Top Silk Screen") (color "White"))
			(layer "F.Paste" (type "Top Solder Paste"))
			(layer "F.Mask" (type "Top Solder Mask") (color "Black") (thickness 0.01))
			(layer "F.Cu" (type "copper") (thickness 0.035))
			(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
			(layer "B.Cu" (type "copper") (thickness 0.035))
			(layer "B.Mask" (type "Bottom Solder Mask") (color "Black") (thickness 0.01))
			(layer "B.Paste" (type "Bottom Solder Paste"))
			(layer "B.SilkS" (type "Bottom Silk Screen") (color "White"))
			(copper_finish "ENIG")
			(dielectric_constraints no)
		)"""


def main():
    ap = argparse.ArgumentParser(description="Generate a 15 cm / 5 inch PCB ruler as a KiCad board.")
    ap.add_argument("--out", default="pcb_ruler.kicad_pcb", help="output .kicad_pcb file")
    ap.add_argument("--black", action="store_true", help="black solder mask, white silkscreen, ENIG finish")
    args = ap.parse_args()

    board = pcbnew.CreateEmptyBoard()
    outline(board)
    metric_scale(board)
    inch_scale(board)
    gauges(board)
    expose_copper(board)
    pcbnew.SaveBoard(args.out, board)
    if args.black:
        text_ = open(args.out, encoding="utf8").read()
        open(args.out, "w", encoding="utf8").write(text_.replace("(setup", BLACK_STACKUP, 1))
    print(f"{len(board.GetDrawings())} objects written to {args.out}")


if __name__ == "__main__":
    main()
