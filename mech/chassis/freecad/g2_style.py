"""STEM-E chassis, saddle body variant, built in FreeCAD.

Same running gear as the CadQuery model (wheelbase, track, H65 wheels, corner
modules, door width, ground clearance all come from ``params.py``), with the
body re-drawn after the AgiBot G2 base: two tall side pods over the wheels and
a low channel down the middle that carries the waist.

Run headless, writes FCStd + STEP into ``../export/freecad/``::

    freecadcmd g2_style.py

Run in the GUI, additionally writes colours into the FCStd and renders views::

    xvfb-run -a freecad g2_style.py        # or open it from the macro menu

Only the body is new here; numbers that already exist live in params.py and
are imported, so the two models cannot drift on the shared geometry.
"""

import math
import os
import sys

import FreeCAD as App
import Part
from FreeCAD import Vector as V

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import params as P  # noqa: E402

OUT = os.path.join(os.path.dirname(HERE), P.EXPORT_DIR, "freecad")

# --------------------------------------------------------------------------
# Saddle body.  Everything not listed here is the running gear's, from params.
# --------------------------------------------------------------------------

# The channel has to take the column flange: 8 x M8 on PCD 200, so a 240
# flange, plus room for the waist to pitch forward into it.  The pods outboard
# of it have to swallow the corner modules, whose housings reach in to
# TRACK/2 - HOUSING_W/2 = 164; the inner wall stays outside that by the skin
# and a gap, including at the top of the draft.
TROUGH_HW = 150.0                    # channel half width at the floor
POD_DRAFT_IN = 6.0                   # inner wall leans outward going up
POD_DRAFT_OUT = 12.0                 # outer wall leans inward going up
POD_TOP_Z = 440.0                    # side pod roof
POD_TOP_R = 28.0                     # roll from pod roof into its walls
CHANNEL_Z = 300.0                    # channel floor: the new lift column seat
CHANNEL_FILLET = 18.0                # concave run from channel floor into pod

assert TROUGH_HW + P.SHELL_T + 5.0 < P.TRACK / 2 - P.HOUSING_W / 2, (
    "channel wall cuts into the corner module housing")
assert TROUGH_HW + POD_DRAFT_IN + P.SHELL_T + 5.0 < P.TRACK / 2 - P.HOUSING_W / 2
assert P.BODY_W / 2 - POD_DRAFT_OUT - P.SHELL_T - 5.0 > P.TRACK / 2 + P.HOUSING_W / 2
assert CHANNEL_Z - P.TOP_PLATE_T > P.BASE_PLATE_Z0 + P.BASE_PLATE_T + 160.0, (
    "centre bay no longer takes the 160 high electronics boxes")
assert P.COLUMN_PCD + 40.0 <= 2 * TROUGH_HW - 2 * 22.0, (
    "column flange does not fit on the channel cover")

# Two packs, one per pod, lifted out through a hatch in the pod roof (hot
# swap, as on the G2).  Each sits between the front and rear steering sweeps.
POD_BATT_L = 2 * (P.WHEELBASE / 2 - P.SWEEP_CLEAR_R - 12.0)
POD_BATT_W = 110.0
POD_BATT_H = 230.0
POD_BATT_Y = P.TRACK / 2
POD_BATT_Z0 = P.BASE_PLATE_Z0 + P.BASE_PLATE_T + 8.0
assert POD_BATT_Z0 + POD_BATT_H < POD_TOP_Z - 40.0, "no room for the handle"
HATCH_L = POD_BATT_L + 20.0
HATCH_W = 100.0

LIDAR_D = 76.0                       # 270 degree scanner, diagonal corners
LIDAR_H = 48.0
CAM_W, CAM_H = 140.0, 40.0           # front depth camera in the channel face


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def rrect(x0, x1, y0, y1, z, r):
    """Closed rounded rectangle wire in the plane z."""
    r = min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01)
    p = [V(x0 + r, y0, z), V(x1 - r, y0, z), V(x1, y0 + r, z), V(x1, y1 - r, z),
         V(x1 - r, y1, z), V(x0 + r, y1, z), V(x0, y1 - r, z), V(x0, y0 + r, z)]
    c = [V(x1 - r, y0 + r, z), V(x1 - r, y1 - r, z),
         V(x0 + r, y1 - r, z), V(x0 + r, y0 + r, z)]
    k = r * (1 - 1 / math.sqrt(2))
    mids = [V(x1 - k, y0 + k, z), V(x1 - k, y1 - k, z),
            V(x0 + k, y1 - k, z), V(x0 + k, y0 + k, z)]
    e = []
    for i in range(4):
        e.append(Part.LineSegment(p[2 * i], p[2 * i + 1]).toShape())
        e.append(Part.Arc(p[2 * i + 1], mids[i], p[(2 * i + 2) % 8]).toShape())
    return Part.Wire(e)


def slab(x0, x1, y0, y1, z0, z1, r, shrink_top=(0, 0, 0, 0)):
    """Rounded box, optionally drafted: shrink_top = (dx0, dx1, dy0, dy1)."""
    a = rrect(x0, x1, y0, y1, z0, r)
    b = rrect(x0 + shrink_top[0], x1 - shrink_top[1],
              y0 + shrink_top[2], y1 - shrink_top[3], z1, r)
    return Part.makeLoft([a, b], True, True)


def try_fillet(shape, r, pick):
    edges = [e for e in shape.Edges if pick(e)]
    if not edges:
        return shape
    try:
        return shape.makeFillet(r, edges)
    except Exception as exc:  # OCC refuses some blends; keep the sharp edge
        App.Console.PrintWarning("fillet %.0f skipped: %s\n" % (r, exc))
        return shape


def cyl(r, h, base, axis=V(0, 0, 1)):
    return Part.makeCylinder(r, h, base, axis)


# --------------------------------------------------------------------------
# Running gear, simplified, positions from params
# --------------------------------------------------------------------------

def wheel(x, y):
    w = P.HUB_TREAD_W
    tire = cyl(P.HUB_TIRE_OD / 2, w, V(x, y - w / 2, P.WHEEL_AXIS_Z), V(0, 1, 0))
    tire = try_fillet(tire, 9.0, lambda e: True)
    hub = cyl(P.HUB_RIM_OD / 2 - 6, P.HUB_OVERALL_W - 8,
              V(x, y - w / 2 - 4 if y < 0 else y + w / 2 + 4 - (P.HUB_OVERALL_W - 8),
                P.WHEEL_AXIS_Z), V(0, 1, 0))
    return tire, hub


def corner_module(x, y):
    """Yoke, kingpin housing and steering motor, as envelopes."""
    sgn = 1 if y > 0 else -1
    plate_y = y - sgn * (P.HUB_FLANGE_OFFSET + P.YOKE_PLATE_T / 2)
    plate = Part.makeBox(P.YOKE_WEB_W, P.YOKE_PLATE_T,
                         P.YOKE_TOP_Z1 - P.WHEEL_AXIS_Z + 26,
                         V(x - P.YOKE_WEB_W / 2, plate_y - P.YOKE_PLATE_T / 2,
                           P.WHEEL_AXIS_Z - 26))
    top = Part.makeBox(P.YOKE_TOP_W, abs(y - plate_y) + 20, P.YOKE_TOP_T,
                       V(x - P.YOKE_TOP_W / 2, min(y, plate_y) - 10, P.YOKE_TOP_Z0))
    housing = Part.makeBox(P.HOUSING_L, P.HOUSING_W, P.HOUSING_Z1 - P.HOUSING_Z0,
                           V(x - P.HOUSING_L / 2, y - P.HOUSING_W / 2, P.HOUSING_Z0))
    tube = cyl(P.KINGPIN_OD / 2, P.KINGPIN_Z1 - P.KINGPIN_Z0, V(x, y, P.KINGPIN_Z0))
    motor = cyl(P.STEER_OD / 2, P.STEER_LEN, V(x, y, P.STEER_OUT_Z))
    return plate.fuse([top, housing, tube, motor]).removeSplitter()


# --------------------------------------------------------------------------
# Body
# --------------------------------------------------------------------------

L2 = P.SHELL_L / 2
W2 = P.BODY_W / 2
# The well is the steering sweep, only as high as the tire crown at full bump.
# Above that nothing turns at the skin's radius, so a taller well would only
# punch a notch through the top of the arch and the band.  params asserts the
# arch swallows the sweep over exactly this height.
WELL_R = P.SWEEP_CLEAR_R
WELL_TOP_Z = P.WHEEL_AXIS_Z + P.SUSP_TRAVEL_MECH + P.HUB_TIRE_OD / 2


def wheel_cuts():
    cuts = []
    for _, x, y in P.CORNERS:
        cuts.append(cyl(WELL_R, WELL_TOP_Z - P.SKIRT_BOTTOM_Z + 1,
                        V(x, y, P.SKIRT_BOTTOM_Z - 1)))
        sgn = 1 if y > 0 else -1
        y0 = P.ARCH_INNER_Y * sgn
        cuts.append(cyl(P.ARCH_R, 200, V(x, y0 if sgn > 0 else y0 - 200, P.ARCH_CZ),
                        V(0, 1, 0)))
    return cuts


def skirt():
    t = P.SHELL_BOTTOM_TUCK
    s = slab(-L2 + t, L2 - t, -W2 + t, W2 - t, P.SKIRT_BOTTOM_Z, P.SHELL_SKIRT_TOP,
             P.SHELL_FILLET, shrink_top=(-t, -t, -t, -t))
    s = s.cut(wheel_cuts())
    # lidar pockets at the two diagonal corners, front camera window
    for name in P.LIDAR_CORNERS:
        sx = 1 if name[0] == "F" else -1
        sy = 1 if name[1] == "L" else -1
        cx = sx * (L2 - P.SHELL_FILLET * 0.75)
        cy = sy * (W2 - P.SHELL_FILLET * 0.75)
        pocket = cyl(LIDAR_D / 2 + 10, LIDAR_H + 6,
                     V(cx, cy, P.SHELL_SKIRT_TOP - LIDAR_H - 10))
        s = s.cut(pocket)
    return s


def belt():
    o = P.SHELL_BELT_OUT
    b = slab(-L2 - o, L2 + o, -W2 - o, W2 + o, P.SHELL_SKIRT_TOP, P.SHELL_BELT_TOP,
             P.SHELL_FILLET + o)
    return b


def channel_floor():
    """The full width white volume from the belt up to the channel floor."""
    return slab(-L2, L2, -W2, W2, P.SHELL_BELT_TOP, CHANNEL_Z, P.SHELL_FILLET)


def pod(sgn):
    yi, yo = TROUGH_HW, W2
    y0, y1 = (yi, yo) if sgn > 0 else (-yo, -yi)
    shrink = ((POD_DRAFT_OUT, POD_DRAFT_OUT,
               POD_DRAFT_IN if sgn > 0 else POD_DRAFT_OUT,
               POD_DRAFT_OUT if sgn > 0 else POD_DRAFT_IN))
    # outer corners carry the body fillet, so the plan shape is the body's;
    # the inner corners are tighter, the channel reads as cut, not moulded
    p = slab(-L2, L2, y0, y1, P.SHELL_BELT_TOP, POD_TOP_Z, P.SHELL_FILLET,
             shrink_top=shrink)
    p = try_fillet(p, POD_TOP_R,
                   lambda e: abs(e.BoundBox.ZMin - POD_TOP_Z) < 0.5
                   and abs(e.BoundBox.ZMax - POD_TOP_Z) < 0.5)
    return p


def upper_body():
    body = channel_floor().fuse([pod(+1), pod(-1)]).removeSplitter()
    # concave run from the channel floor up the pod walls
    body = try_fillet(body, CHANNEL_FILLET,
                      lambda e: abs(e.BoundBox.ZMin - CHANNEL_Z) < 0.5
                      and abs(e.BoundBox.ZMax - CHANNEL_Z) < 0.5
                      and e.BoundBox.XLength > P.SHELL_L * 0.7
                      and abs(abs(e.BoundBox.Center.y) - TROUGH_HW) < 2.0)
    # hatches let into the pod roofs
    for sgn in (1, -1):
        y = sgn * (POD_BATT_Y)
        body = body.cut(Part.makeBox(HATCH_L + 4, HATCH_W + 4, 3,
                                     V(-HATCH_L / 2 - 2, y - HATCH_W / 2 - 2,
                                       POD_TOP_Z - 2)))
    # front camera window in the face under the channel
    body = body.cut(Part.makeBox(20, CAM_W, CAM_H,
                                 V(L2 - 10, -CAM_W / 2, (P.SHELL_BELT_TOP + CHANNEL_Z) / 2
                                   - CAM_H / 2)))
    return body


def hatches():
    out = []
    for sgn in (1, -1):
        y = sgn * POD_BATT_Y
        h = slab(-HATCH_L / 2, HATCH_L / 2, y - HATCH_W / 2, y + HATCH_W / 2,
                 POD_TOP_Z - 2, POD_TOP_Z + 0.5, 14)
        grip = Part.makeBox(70, 22, 4, V(-35, y - 11, POD_TOP_Z - 3.0))
        out.append(h.cut(grip))
    return out


def channel_cover():
    """Dark pad on the channel floor with the lift column interface."""
    pad = slab(-L2 + 70, L2 - 70, -TROUGH_HW + 22, TROUGH_HW - 22,
               CHANNEL_Z, CHANNEL_Z + 1.5, 40)
    holes = [cyl(4.5, 10, V(P.COLUMN_PCD / 2 * math.cos(a), P.COLUMN_PCD / 2 * math.sin(a),
                            CHANNEL_Z - 4))
             for a in (2 * math.pi * i / P.COLUMN_BOLTS + math.pi / P.COLUMN_BOLTS
                       for i in range(P.COLUMN_BOLTS))]
    spigot = cyl(P.COLUMN_SPIGOT_OD / 2, 10, V(0, 0, CHANNEL_Z - 4))
    return pad.cut(holes + [spigot])


def column_ghost():
    """Where the lift column stands; not designed here, only located."""
    flange = cyl(P.COLUMN_PCD / 2 + 20, 12, V(0, 0, CHANNEL_Z + 1.5))
    body = slab(-80, 80, -100, 100, CHANNEL_Z + 13.5, CHANNEL_Z + 260, 30)
    return flange.fuse(body)


def lidars():
    out = []
    for name in P.LIDAR_CORNERS:
        sx = 1 if name[0] == "F" else -1
        sy = 1 if name[1] == "L" else -1
        cx = sx * (L2 - P.SHELL_FILLET * 0.75)
        cy = sy * (W2 - P.SHELL_FILLET * 0.75)
        out.append(cyl(LIDAR_D / 2, LIDAR_H, V(cx, cy, P.SHELL_SKIRT_TOP - LIDAR_H - 7)))
    return out


def batteries():
    return [Part.makeBox(POD_BATT_L, POD_BATT_W, POD_BATT_H,
                         V(-POD_BATT_L / 2, s * POD_BATT_Y - POD_BATT_W / 2, POD_BATT_Z0))
            for s in (1, -1)]


def estop():
    x, y = -L2 + 70, -(TROUGH_HW + W2) / 2
    base = cyl(26, 10, V(x, y, POD_TOP_Z - 6))
    cap = Part.makeSphere(22, V(x, y, POD_TOP_Z + 4))
    cap = cap.common(Part.makeBox(60, 60, 30, V(x - 30, y - 30, POD_TOP_Z + 4)))
    return base, cap


# --------------------------------------------------------------------------
# Assemble
# --------------------------------------------------------------------------

COLORS = {
    "skirt": (0.20, 0.21, 0.23), "belt": (0.05, 0.05, 0.06),
    "upper": (0.93, 0.93, 0.91), "hatch": (0.30, 0.31, 0.33),
    "cover": (0.25, 0.26, 0.28), "column": (0.35, 0.55, 0.85),
    "tire": (0.08, 0.08, 0.08), "hub": (0.70, 0.71, 0.73),
    "module": (0.62, 0.64, 0.68), "battery": (0.95, 0.65, 0.15),
    "lidar": (0.10, 0.10, 0.12), "estop_base": (0.95, 0.80, 0.10),
    "estop": (0.85, 0.08, 0.08),
}


def build():
    doc = App.newDocument("STEM_E_chassis_saddle")
    parts = []

    def add(name, shape, color, group=None, transparency=0):
        obj = doc.addObject("Part::Feature", name)
        obj.Shape = shape
        if group is not None:
            group.addObject(obj)
        parts.append((obj, color, transparency))
        return obj

    g_body = doc.addObject("App::DocumentObjectGroup", "Body")
    g_gear = doc.addObject("App::DocumentObjectGroup", "RunningGear")
    g_inner = doc.addObject("App::DocumentObjectGroup", "Internals")

    add("Skirt", skirt(), COLORS["skirt"], g_body)
    add("Belt", belt(), COLORS["belt"], g_body)
    add("UpperBody", upper_body(), COLORS["upper"], g_body)
    for i, h in enumerate(hatches()):
        add("BatteryHatch_%s" % "LR"[i], h, COLORS["hatch"], g_body)
    add("ChannelCover", channel_cover(), COLORS["cover"], g_body)
    for i, l in enumerate(lidars()):
        add("Lidar_%s" % P.LIDAR_CORNERS[i], l, COLORS["lidar"], g_body)
    b, c = estop()
    add("EStopBase", b, COLORS["estop_base"], g_body)
    add("EStop", c, COLORS["estop"], g_body)

    for name, x, y in P.CORNERS:
        tire, hub = wheel(x, y)
        add("Tire_" + name, tire, COLORS["tire"], g_gear)
        add("Hub_" + name, hub, COLORS["hub"], g_gear)
        add("CornerModule_" + name, corner_module(x, y), COLORS["module"], g_gear)

    for i, bt in enumerate(batteries()):
        add("Battery_%s" % "LR"[i], bt, COLORS["battery"], g_inner)
    add("LiftColumn_ghost", column_ghost(), COLORS["column"], g_inner, 60)

    sheet = doc.addObject("Spreadsheet::Sheet", "Params")
    rows = [("WHEELBASE", P.WHEELBASE), ("TRACK", P.TRACK),
            ("SHELL_L", P.SHELL_L), ("BODY_W_MAX", P.BODY_W_MAX),
            ("GROUND_CLEARANCE", P.GROUND_CLEARANCE), ("TROUGH_HW", TROUGH_HW),
            ("CHANNEL_Z", CHANNEL_Z), ("POD_TOP_Z", POD_TOP_Z),
            ("POD_BATT_L", POD_BATT_L), ("POD_BATT_W", POD_BATT_W),
            ("POD_BATT_H", POD_BATT_H)]
    sheet.set("A1", "name")
    sheet.set("B1", "mm")
    for i, (k, v) in enumerate(rows, start=2):
        sheet.set("A%d" % i, k)
        sheet.set("B%d" % i, "%.1f" % v)
    doc.recompute()
    return doc, parts


def report(doc):
    lines = []
    bb = None
    for o in doc.Objects:
        if hasattr(o, "Shape") and o.Shape.isValid() and o.Shape.Volume > 0:
            bb = o.Shape.BoundBox if bb is None else bb.united(o.Shape.BoundBox)
    lines.append("envelope  L %.0f  W %.0f  H %.0f mm"
                 % (bb.XLength, bb.YLength, POD_TOP_Z))
    lines.append("channel   %.0f wide, floor z %.0f (was deck %.0f, %.0f lower)"
                 % (2 * TROUGH_HW, CHANNEL_Z, P.DECK_Z, P.DECK_Z - CHANNEL_Z))
    lines.append("pods      roof z %.0f, %.0f above the channel"
                 % (POD_TOP_Z, POD_TOP_Z - CHANNEL_Z))
    v = POD_BATT_L * POD_BATT_W * POD_BATT_H / 1e6
    lines.append("packs     2 x %.0f x %.0f x %.0f = 2 x %.1f L"
                 % (POD_BATT_L, POD_BATT_W, POD_BATT_H, v))
    # the packs must not meet the corner modules or the wheels
    movers = [o for o in doc.Objects if o.Name.startswith(("CornerModule", "Tire"))]
    for o in doc.Objects:
        if o.Name.startswith("Battery"):
            for m in movers:
                d = o.Shape.distToShape(m.Shape)[0]
                assert d > 3.0, "%s within %.1f of %s" % (o.Name, d, m.Name)
    for o in doc.Objects:
        if o.Name.startswith("Tire"):
            for s in ("Skirt", "Belt", "UpperBody"):
                d = o.Shape.distToShape(doc.getObject(s).Shape)[0]
                assert d > 2.0, "%s within %.1f of %s" % (o.Name, d, s)
    lines.append("checks    packs clear modules and tires, tires clear body: ok")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    doc, parts = build()
    txt = report(doc)
    print(txt)
    with open(os.path.join(OUT, "report.txt"), "w") as f:
        f.write(txt + "\n")

    if App.GuiUp:
        import FreeCADGui as Gui
        for obj, color, transp in parts:
            vo = obj.ViewObject
            vo.ShapeColor = color
            vo.Transparency = transp
            if obj.Name.startswith(("Battery", "CornerModule")):
                vo.Visibility = False

    doc.saveAs(os.path.join(OUT, "stem_e_chassis_saddle.FCStd"))
    shapes = [o for o in doc.Objects if o.TypeId == "Part::Feature"]
    Part.export(shapes, os.path.join(OUT, "stem_e_chassis_saddle.step"))

    if App.GuiUp:
        render_views(doc)


def render_views(doc):
    import FreeCADGui as Gui
    Gui.ActiveDocument = Gui.getDocument(doc.Name)
    view = Gui.ActiveDocument.ActiveView
    view.setAnimationEnabled(False)
    view.setCameraType("Orthographic")
    view.setAxisCross(False)

    def shot(name, setter):
        setter()
        Gui.updateGui()
        view.fitAll()
        Gui.updateGui()
        view.saveImage(os.path.join(OUT, name + ".png"), 1600, 1000, "#F4F5F7")

    shot("iso_front", view.viewIsometric)
    shot("iso_rear", lambda: view.setCameraOrientation(
        App.Rotation(V(0, 0, 1), -135).multiply(App.Rotation(V(1, 0, 0), 60)).Q))
    # base_link is +X forward, so the robot's front is FreeCAD's "right" view
    shot("front", view.viewRight)
    shot("side", view.viewFront)
    shot("top", view.viewTop)

    # x-ray: make the body see-through, show what sits inside
    for o in doc.Objects:
        if o.TypeId != "Part::Feature":
            continue
        vo = o.ViewObject
        if o.Name.startswith(("Battery", "CornerModule")):
            vo.Visibility = True
        elif o.Name in ("Skirt", "Belt", "UpperBody", "ChannelCover") \
                or o.Name.startswith("BatteryHatch"):
            vo.Transparency = 75
    shot("xray", view.viewIsometric)
    for o in doc.Objects:
        if o.TypeId == "Part::Feature" and not o.Name.startswith("LiftColumn"):
            o.ViewObject.Transparency = 0
            if o.Name.startswith(("Battery", "CornerModule")):
                o.ViewObject.Visibility = False


main()
if App.GuiUp and os.environ.get("STEM_FC_QUIT", "1") == "1" \
        and os.environ.get("STEM_FC_BATCH"):
    os._exit(0)
