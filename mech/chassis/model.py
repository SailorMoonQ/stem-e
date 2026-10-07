"""Parametric CadQuery model of the STEM-E 4WS chassis.

Every dimension comes from ``params``; nothing is hardcoded here.  Run
``build.py`` to emit STEP, STL and SVG into ``export/``.

Frame: +X forward, +Y left, +Z up, origin on the ground at the centre of the
four contact patches.  A corner module is modelled in a local frame with the
kingpin axis on local Z and the wheel axis on local Y, then placed at each
corner; right hand corners are mirrored about the XZ plane.
"""

import math

import cadquery as cq

import params as P

ALU = cq.Color(0.72, 0.74, 0.76)
STEEL = cq.Color(0.45, 0.46, 0.48)
RUBBER = cq.Color(0.17, 0.17, 0.18)


def _lighten(plate, z0, t, half_x, half_y, keepouts):
    """Punch a grid of pockets, skipping anything inside a keepout rectangle."""
    pts = []
    n_x = int(half_x // P.LIGHTEN_PITCH)
    n_y = int(half_y // P.LIGHTEN_PITCH)
    margin = P.LIGHTEN_D / 2 + 14
    for i in range(-n_x, n_x + 1):
        for j in range(-n_y, n_y + 1):
            x, y = i * P.LIGHTEN_PITCH, j * P.LIGHTEN_PITCH
            if abs(x) > half_x - margin or abs(y) > half_y - margin:
                continue
            if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, x1, y0, y1 in keepouts):
                continue
            pts.append((x, y))
    if not pts:
        return plate
    holes = (
        cq.Workplane("XY", origin=(0, 0, z0))
        .pushPoints(pts)
        .circle(P.LIGHTEN_D / 2)
        .extrude(t)
    )
    return plate.cut(holes)


def _truss(solid, normal, const, z_mid, span, exclude_abs):
    """Punch a row of holes through a vertical web to turn it into a truss.

    ``normal`` is "Y" for the side spines or "X" for the cross members;
    ``const`` is that coordinate, ``span`` the half length along the web.
    """
    n = int(span // P.WEB_HOLE_PITCH)
    cut = None
    for i in range(-n, n + 1):
        u = i * P.WEB_HOLE_PITCH
        if abs(u) > span - P.WEB_HOLE_D / 2 - 20 or abs(u) < exclude_abs:
            continue
        if normal == "Y":
            wp = cq.Workplane("XZ", origin=(u, const, z_mid))
        else:
            wp = cq.Workplane("YZ", origin=(const, u, z_mid))
        hole = wp.circle(P.WEB_HOLE_D / 2).extrude(60, both=True)
        cut = hole if cut is None else cut.union(hole)
    return solid if cut is None else solid.cut(cut)


def _polar(pcd, angles):
    r = pcd / 2.0
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in angles]


# ---------------------------------------------------------------- components

def hub_motor():
    """DM-H65 envelope, wheel axis on local Y, centre plane at Y = 0."""
    # "XZ" normal points at -Y, so a positive extrude travels inboard, which is
    # the side the mounting flange lives on.
    far = P.HUB_OVERALL_W - P.HUB_FLANGE_OFFSET          # 28.46 outboard of centre
    tire = cq.Workplane("XZ").circle(P.HUB_TIRE_OD / 2).extrude(P.HUB_TREAD_W / 2, both=True)
    rim = cq.Workplane("XZ").circle(P.HUB_RIM_OD / 2).extrude(P.HUB_TREAD_W / 2 + 2, both=True)
    cover = cq.Workplane("XZ").circle(P.HUB_RIM_OD / 2 - 2).extrude(-far)
    stator = cq.Workplane("XZ").circle(P.HUB_RIM_OD / 2 - 8).extrude(P.HUB_FLANGE_OFFSET - 2)
    boss = (
        cq.Workplane("XZ", origin=(0, -(P.HUB_FLANGE_OFFSET - 2), 0))
        .circle(P.HUB_FLANGE_BOSS_OD / 2)
        .extrude(2)
    )
    whole = tire.union(rim).union(cover).union(stator).union(boss)
    return whole.translate((0, 0, P.WHEEL_AXIS_Z))


def steering_yoke():
    """CNC aluminium yoke: hub flange pad, riser web, top plate."""
    y1 = -P.HUB_FLANGE_OFFSET                 # -37.84, flange mounting face
    y0 = y1 - P.YOKE_PLATE_T                  # -53.84
    web = (
        cq.Workplane("XY")
        .box(90, P.YOKE_PLATE_T, P.YOKE_TOP_Z1 - 37.5, centered=(True, False, False))
        .translate((0, y0, 37.5))
    )
    top = (
        cq.Workplane("XY")
        .box(104, 88.84, P.YOKE_TOP_T, centered=(True, False, False))
        .translate((0, y0, P.YOKE_TOP_Z0))
    )
    yoke = web.union(top)

    pad = cq.Workplane("XZ", origin=(0, y1, P.WHEEL_AXIS_Z))
    for d, pts in (
        (5.5, _polar(P.HUB_FLANGE_PCD, P.HUB_FLANGE_M5_ANGLES)),
        (P.HUB_FLANGE_DOWEL_D, _polar(P.HUB_FLANGE_PCD, P.HUB_FLANGE_DOWEL_ANGLES)),
    ):
        yoke = yoke.cut(pad.pushPoints(pts).circle(d / 2).extrude(P.YOKE_PLATE_T))
    yoke = yoke.cut(pad.circle(10).extrude(P.YOKE_PLATE_T))          # cable pass

    bore = (
        cq.Workplane("XY", origin=(0, 0, P.YOKE_TOP_Z0))
        .circle(P.KINGPIN_ID / 2)
        .extrude(P.YOKE_TOP_T)
    )
    bolts = (
        cq.Workplane("XY", origin=(0, 0, P.YOKE_TOP_Z0))
        .pushPoints(_polar(P.TUBE_FLANGE_PCD, range(0, 360, 60)))
        .circle(2.5)
        .extrude(P.YOKE_TOP_T)
    )
    return yoke.cut(bore).cut(bolts)


def kingpin_tube():
    """Hollow kingpin.  The cable runs up the bore and twists near the axis."""
    z0, z1 = P.KINGPIN_Z0, P.KINGPIN_Z1
    tube = cq.Workplane("XY", origin=(0, 0, z0 + 6)).circle(P.KINGPIN_OD / 2).extrude(z1 - z0 - 6)
    top = cq.Workplane("XY", origin=(0, 0, z1)).circle(P.TUBE_FLANGE_OD / 2).extrude(P.TUBE_FLANGE_T)
    ring = cq.Workplane("XY", origin=(0, 0, z0)).circle(P.TUBE_FLANGE_OD / 2).extrude(6)
    body = tube.union(top).union(ring)
    bore = (
        cq.Workplane("XY", origin=(0, 0, z0))
        .circle(P.KINGPIN_ID / 2)
        .extrude(z1 + P.TUBE_FLANGE_T - z0)
    )
    window = cq.Workplane("XZ", origin=(0, 0, z1 - 16)).circle(7).extrude(P.KINGPIN_OD, both=True)
    return body.cut(bore).cut(window)


def bearing_housing():
    """Frame side block carrying the two 6810 bearings and the rail carriages."""
    z0, z1 = P.HOUSING_Z0, P.HOUSING_Z1
    blk = (
        cq.Workplane("XY", origin=(0, 0, z0))
        .box(P.HOUSING_L, P.HOUSING_W, z1 - z0, centered=(True, True, False))
    )
    bore = cq.Workplane("XY", origin=(0, 0, z0)).circle(P.BEARING_OD / 2).extrude(z1 - z0)
    blk = blk.cut(bore)
    for sx in (-1.0, 1.0):
        blk = blk.union(
            cq.Workplane("XY", origin=(sx * P.SUSP_SPRING_X, P.SUSP_SPRING_Y, z1 - 14))
            .circle(P.LOADCELL_OD / 2 + 4)
            .extrude(14)
        )
    return blk


def steer_motor():
    """DM-J4340-2EC envelope, output face down at STEER_OUT_Z."""
    return (
        cq.Workplane("XY", origin=(0, 0, P.STEER_OUT_Z))
        .circle(P.STEER_OD / 2)
        .extrude(P.STEER_LEN)
    )


def steer_bracket():
    """Hangs the steering motor off the housing and reacts its torque."""
    plate = (
        cq.Workplane("XY", origin=(0, 0, P.STEER_REAR_Z))
        .box(2 * P.STEER_BRACKET_HALF_X, P.HOUSING_W, P.STEER_BRACKET_T,
             centered=(True, True, False))
    )
    plate = plate.cut(
        cq.Workplane("XY", origin=(0, 0, P.STEER_REAR_Z))
        .circle(P.STEER_REAR_SPIGOT_OD / 2)
        .extrude(P.STEER_BRACKET_T)
    )
    posts = None
    for x, y in ((-26, -38), (-26, 38), (26, -38), (26, 38)):
        post = (
            cq.Workplane("XY", origin=(x, y, P.HOUSING_Z1))
            .circle(9)
            .extrude(P.STEER_REAR_Z - P.HOUSING_Z1)
        )
        posts = post if posts is None else posts.union(post)
    return plate.union(posts)


def suspension():
    """Two vertical rails plus one spring and load cell, inboard of the kingpin.

    The rails start above ``YOKE_TOP_Z1``: below that height the yoke sweeps a
    74.6 mm radius about the kingpin and would hit them.
    """
    rails = None
    for x in (-P.RAIL_PITCH_X / 2, P.RAIL_PITCH_X / 2):
        rail = (
            cq.Workplane("XY", origin=(x, P.RAIL_Y, P.RAIL_Z0))
            .box(12, 12, P.RAIL_LEN, centered=(True, True, False))
        )
        rails = rail if rails is None else rails.union(rail)
    free = P.TOP_PLATE_Z0 - (P.HOUSING_Z1 + P.LOADCELL_H)   # deck is the spring seat
    cell = spring = None
    for sx in (-1.0, 1.0):
        pos = (sx * P.SUSP_SPRING_X, P.SUSP_SPRING_Y)
        c = (
            cq.Workplane("XY", origin=(pos[0], pos[1], P.HOUSING_Z1))
            .circle(P.LOADCELL_OD / 2)
            .extrude(P.LOADCELL_H)
        )
        s = (
            cq.Workplane("XY", origin=(pos[0], pos[1], P.HOUSING_Z1 + P.LOADCELL_H))
            .circle(P.SPRING_OD / 2)
            .extrude(free)
        )
        cell = c if cell is None else cell.union(c)
        spring = s if spring is None else spring.union(s)
    return rails, cell, spring


# ------------------------------------------------------------------ assembly

def corner_module(name, mirror):
    """Local frame module.  ``mirror`` flips it for the right hand corners."""
    rails, cell, spring = suspension()
    parts = [
        ("wheel", hub_motor(), RUBBER),
        ("yoke", steering_yoke(), ALU),
        ("kingpin", kingpin_tube(), cq.Color(0.80, 0.62, 0.20)),
        ("housing", bearing_housing(), ALU),
        ("steer_motor", steer_motor(), cq.Color(0.27, 0.51, 0.71)),
        ("steer_bracket", steer_bracket(), ALU),
        ("rails", rails, STEEL),
        ("loadcell", cell, cq.Color(0.80, 0.36, 0.36)),
        ("spring", spring, cq.Color(0.56, 0.74, 0.56)),
    ]
    asm = cq.Assembly(name=name)
    for pname, solid, colour in parts:
        s = solid.mirror("XZ") if mirror else solid
        asm.add(s, name=name + "_" + pname, color=colour)
    return asm


def _sweep_clearance():
    """Union of the four cylinders the steering modules turn inside."""
    cut = None
    for _, x, y in P.CORNERS:
        cyl = (
            cq.Workplane("XY", origin=(x, y, 0))
            .circle(P.SWEEP_CLEAR_R)
            .extrude(P.SWEEP_CLEAR_Z)
        )
        cut = cyl if cut is None else cut.union(cyl)
    return cut


def _bays():
    """Centres of the two equipment bays, outboard of the cross members."""
    inner, outer = P.CROSS_X + P.SPINE_T / 2, (P.BODY_L - 40) / 2 - 10
    c = (inner + outer) / 2
    return (-c, c)


def frame():
    """Base plate, two side spines, two cross members, top deck.

    The side spines carry the suspension rails, so each corner module hangs off
    a continuous plate rather than a bracket.  The cross members sit at
    ``CROSS_X`` so that they frame the lift column footprint: the column's base
    moment goes straight into the webs instead of bending the bare deck, which
    ``frame_budget.py`` shows is the softest path in the whole frame.
    """
    bay_a, bay_f = _bays()
    base = (
        cq.Workplane("XY", origin=(0, 0, P.BASE_PLATE_Z0))
        .box(P.BASE_PLATE_L, P.BASE_PLATE_W, P.BASE_PLATE_T, centered=(True, True, False))
    )
    base = _lighten(
        base, P.BASE_PLATE_Z0, P.BASE_PLATE_T, P.BASE_PLATE_L / 2, P.BASE_PLATE_W / 2,
        keepouts=[
            (P.REAR_BAY_X - 130, P.REAR_BAY_X + 130, -150, 150),
            (-P.CROSS_X - 30, P.CROSS_X + 30, -P.SPINE_Y, P.SPINE_Y),
        ],
    )

    top_l, top_w = P.BODY_L - 40, P.BODY_W - 160
    top = (
        cq.Workplane("XY", origin=(0, 0, P.TOP_PLATE_Z0))
        .box(top_l, top_w, P.TOP_PLATE_T, centered=(True, True, False))
    )
    sw, sh = P.SERVICE_OPENING
    for cx in _bays():
        top = top.cut(
            cq.Workplane("XY", origin=(cx, 0, P.TOP_PLATE_Z0))
            .box(sw, sh, P.TOP_PLATE_T, centered=(True, True, False))
            .edges("|Z").fillet(20)
        )
    top = _lighten(
        top, P.TOP_PLATE_Z0, P.TOP_PLATE_T, top_l / 2, top_w / 2,
        keepouts=[(-P.COLUMN_PAD, P.COLUMN_PAD, -P.COLUMN_PAD, P.COLUMN_PAD)],
    )
    top = top.cut(
        cq.Workplane("XY", origin=(0, 0, P.TOP_PLATE_Z0))
        .pushPoints(_polar(P.COLUMN_PCD, range(0, 360, 360 // P.COLUMN_BOLTS)))
        .circle(4.5)
        .extrude(P.TOP_PLATE_T)
    )
    # Doubler under the deck.  The cross members already cut the unsupported
    # span from 260 to 80 mm; doubling the local thickness takes the rest.
    doubler = (
        cq.Workplane("XY", origin=(0, 0, P.TOP_PLATE_Z0 - P.COLUMN_DOUBLER_T))
        .box(P.COLUMN_DOUBLER, P.COLUMN_DOUBLER, P.COLUMN_DOUBLER_T,
             centered=(True, True, False))
        .edges("|Z").fillet(24)
    )
    top = top.union(doubler)
    top = top.cut(
        cq.Workplane("XY", origin=(0, 0, P.TOP_PLATE_Z0 - P.COLUMN_DOUBLER_T))
        .circle(P.COLUMN_SPIGOT_OD / 2)
        .extrude(P.TOP_PLATE_T + P.COLUMN_DOUBLER_T)
    )
    top = top.cut(
        cq.Workplane("XY", origin=(0, 0, P.TOP_PLATE_Z0 - P.COLUMN_DOUBLER_T))
        .pushPoints(_polar(P.COLUMN_PCD, range(0, 360, 360 // P.COLUMN_BOLTS)))
        .circle(4.5)
        .extrude(P.TOP_PLATE_T + P.COLUMN_DOUBLER_T)
    )

    out = base.union(top)
    for sy in (1.0, -1.0):
        y = sy * P.SPINE_Y
        out = out.union(
            cq.Workplane("XY", origin=(0, y, P.SWEEP_CLEAR_Z))
            .box(P.BODY_L - 80, P.SPINE_T, P.TOP_PLATE_Z0 - P.SWEEP_CLEAR_Z,
                 centered=(True, True, False))
        )
        out = out.union(
            cq.Workplane("XY", origin=(0, y, P.BASE_PLATE_Z0 + P.BASE_PLATE_T))
            .box(P.BODY_L - 220, P.SPINE_T, P.SWEEP_CLEAR_Z - P.BASE_PLATE_Z0 - P.BASE_PLATE_T,
                 centered=(True, True, False))
        )
    for sx in (1.0, -1.0):
        out = out.union(
            cq.Workplane("XY", origin=(sx * P.CROSS_X, 0, P.BASE_PLATE_Z0 + P.BASE_PLATE_T))
            .box(P.SPINE_T, 2 * P.SPINE_Y, P.TOP_PLATE_Z0 - P.BASE_PLATE_Z0 - P.BASE_PLATE_T,
                 centered=(True, True, False))
        )

    # Turn the solid webs into trusses, keeping material solid where the
    # suspension rails and the corner modules bolt on.
    for sy in (1.0, -1.0):
        out = _truss(out, "Y", sy * P.SPINE_Y, (P.SWEEP_CLEAR_Z + P.TOP_PLATE_Z0) / 2,
                     (P.BODY_L - 80) / 2, exclude_abs=270.0)
        out = _truss(out, "Y", sy * P.SPINE_Y, P.BASE_PLATE_Z0 + 50,
                     (P.BODY_L - 220) / 2, exclude_abs=0.0)
    for sx in (1.0, -1.0):
        out = _truss(out, "X", sx * P.CROSS_X, (P.BASE_PLATE_Z0 + P.TOP_PLATE_Z0) / 2,
                     P.SPINE_Y, exclude_abs=0.0)
    return out.cut(_sweep_clearance())


def _rr(l, w, z, r):
    """Rounded rectangle sketch, placed at a height."""
    return (cq.Sketch().rect(l, w).vertices().fillet(r)
            .moved(cq.Location(cq.Vector(0, 0, z))))


def _loft(sections):
    """Ruled loft through rounded rectangles.  Every face stays developable, so
    the whole skin still folds from flat sheet."""
    wp = cq.Workplane("XY").placeSketch(*[_rr(*s) for s in sections])
    return wp.loft(ruled=True)


def _skin(sections, t):
    """Shell the lofted volume: outer minus the same loft inset by t."""
    outer = _loft(sections)
    inner = _loft([(l - 2 * t, w - 2 * t, z, max(r - t, 1.0))
                   for l, w, z, r in _inner_z(sections)])
    return outer.cut(inner)


def _inner_z(sections):
    """Stretch the inner loft past both ends so the shell is open top and
    bottom rather than capped."""
    out = list(sections)
    out[0] = (out[0][0], out[0][1], out[0][2] - 4, out[0][3])
    out[-1] = (out[-1][0], out[-1][1], out[-1][2] + 4, out[-1][3])
    return out


_F = P.SHELL_FILLET


def _skirt_sections():
    tuck = P.SHELL_BOTTOM_TUCK
    return [
        (P.BODY_L - 2 * tuck, P.BODY_W - 2 * tuck, P.GROUND_CLEARANCE, _F - tuck / 2),
        (P.BODY_L, P.BODY_W, P.GROUND_CLEARANCE + 34, _F),
        (P.BODY_L, P.BODY_W, P.SHELL_SKIRT_TOP, _F),
    ]


def _upper_sections():
    return [
        (P.BODY_L, P.BODY_W, P.SHELL_BELT_TOP, _F),
        (P.SHELL_TOP_L, P.SHELL_TOP_W, P.DECK_Z, _F - 6),
    ]


def _belt_sections():
    i = P.SHELL_BELT_INSET
    return [
        (P.BODY_L - 2 * i, P.BODY_W - 2 * i, P.SHELL_SKIRT_TOP - 2, _F - i),
        (P.BODY_L - 2 * i, P.BODY_W - 2 * i, P.SHELL_BELT_TOP + 2, _F - i),
    ]


def _panel_cuts():
    """Boxes that open the skirt.  Each one also defines the plate that fills it.

    rear layout: one wide door in the aft face for the battery drawer.
    side layout: a door in each flank over its pack, the aft face left to the
    connector panel.
    """
    cuts = []
    if P.BATTERY_LAYOUT == "rear":
        cuts.append(
            cq.Workplane("XY", origin=(-P.BODY_L / 2 - 20, 0, 96))
            .box(70, 300, 100, centered=(True, True, False))
            .edges("|X").fillet(14)
        )
    else:
        for sy in (1.0, -1.0):
            cuts.append(
                cq.Workplane("XY", origin=(0, sy * (P.BODY_W / 2 + 20), 96))
                .box(330, 70, 100, centered=(True, True, False))
                .edges("|Y").fillet(14)
            )
    return cuts


def _io_cut():
    return (
        cq.Workplane("XY", origin=(-P.BODY_L / 2 - 20, 0, P.ESTOP_Z - 20))
        .box(70, P.IO_PANEL[0], P.IO_PANEL[1], centered=(True, True, False))
        .edges("|X").fillet(8)
    )


def _handles():
    out = None
    for sy in (1.0, -1.0):
        for sx in (1.0, -1.0):
            h = (
                cq.Workplane("XY", origin=(sx * 215, sy * (P.BODY_W / 2 + 20), P.HANDLE_Z))
                .box(P.HANDLE[0], 70, P.HANDLE[1], centered=(True, True, False))
                .edges("|Y").fillet(P.HANDLE[1] / 2 - 1)
            )
            out = h if out is None else out.union(h)
    return out


def _vents():
    out = None
    for sy in (1.0, -1.0):
        for i in range(P.VENT_SLOTS):
            x = -150 + i * 22
            v = (
                cq.Workplane("XY", origin=(x, sy * (P.BODY_W / 2 + 20), 100))
                .box(9, 70, 54, centered=(True, True, False))
                .edges("|Y").fillet(4)
            )
            out = v if out is None else out.union(v)
    return out


def shell_skirt():
    """Dark lower volume: wheel arches, rub rail, grips, vents, access doors."""
    s = _skin(_skirt_sections(), P.SHELL_T).cut(_sweep_clearance())
    for c in _panel_cuts():
        s = s.cut(c)
    s = s.cut(_handles()).cut(_vents())

    z0, z1 = P.BUMPER_Z
    o = P.BUMPER_OUT
    rail = _skin([(P.BODY_L + 2 * o, P.BODY_W + 2 * o, z0, _F + o),
                  (P.BODY_L + 2 * o, P.BODY_W + 2 * o, z1, _F + o)], o + P.SHELL_T)
    return s.union(rail.cut(_sweep_clearance()).cut(_handles()))


def shell_upper():
    """Light upper volume, shoulder taper, badge and connector bezel."""
    s = _skin(_upper_sections(), P.SHELL_T).cut(_sweep_clearance()).cut(_io_cut())
    badge = (
        cq.Workplane("XY", origin=(P.BODY_L / 2 - 8, 0, 268))
        .box(6, P.BADGE[0], P.BADGE[1], centered=(True, True, False))
        .edges("|X").fillet(6)
    )
    return s.union(badge)


def shell_belt():
    """Recessed band between the two volumes: parting line and light strip."""
    return _skin(_belt_sections(), P.SHELL_T).cut(_sweep_clearance())


def shell_light():
    """Lit strip sitting in the belt recess, right around the machine.

    Running it front and rear as well as down the sides is what makes the belt
    read as one line instead of two stripes, and it gives the robot a visible
    state from any direction.
    """
    i = P.SHELL_BELT_INSET
    z = (P.SHELL_SKIRT_TOP + P.SHELL_BELT_TOP) / 2 - 5
    out = None
    for sy in (1.0, -1.0):
        seg = (
            cq.Workplane("XY", origin=(0, sy * (P.BODY_W / 2 - i + 1.5), z))
            .box(430, 5, 10, centered=(True, True, False))
        )
        out = seg if out is None else out.union(seg)
    for sx in (1.0, -1.0):
        seg = (
            cq.Workplane("XY", origin=(sx * (P.BODY_L / 2 - i + 1.5), 0, z))
            .box(5, 330, 10, centered=(True, True, False))
        )
        out = out.union(seg)
    return out


def shell_cover():
    """Dark plate on the deck, inset from the shell edge so a reveal shows."""
    i = P.COVER_INSET
    c = (
        cq.Workplane("XY", origin=(0, 0, P.DECK_Z))
        .box(P.SHELL_TOP_L - 2 * i, P.SHELL_TOP_W - 2 * i, P.COVER_T,
             centered=(True, True, False))
        .edges("|Z").fillet(20)
    )
    c = c.cut(
        cq.Workplane("XY", origin=(0, 0, P.DECK_Z))
        .circle(P.COLUMN_SPIGOT_OD / 2)
        .extrude(P.COVER_T)
    )
    c = c.cut(
        cq.Workplane("XY", origin=(0, 0, P.DECK_Z))
        .pushPoints(_polar(P.COLUMN_PCD, range(0, 360, 360 // P.COLUMN_BOLTS)))
        .circle(5)
        .extrude(P.COVER_T)
    )
    return c


def shell():
    """Everything fixed, for mass and clash checking."""
    return shell_skirt().union(shell_upper()).union(shell_belt()).union(shell_cover())


def shell_panels():
    """The plates that come off: battery access and the connector panel."""
    skirt = _skin(_skirt_sections(), P.SHELL_T).cut(_sweep_clearance())
    upper = _skin(_upper_sections(), P.SHELL_T).cut(_sweep_clearance())
    out = None
    for c in _panel_cuts():
        p = skirt.intersect(c)
        out = p if out is None else out.union(p)
    return out.union(upper.intersect(_io_cut()))


def estop():
    """Mushroom head on the aft face.  The torso needs its own; this one only
    covers someone standing behind the base."""
    return (
        cq.Workplane("YZ", origin=(-P.BODY_L / 2 + 10, 0, P.ESTOP_Z + 42))
        .circle(P.ESTOP_OD / 2)
        .extrude(-26)
    )


def _boxes(packs, l, w, h, z0):
    out = None
    for x, y in packs:
        b = (
            cq.Workplane("XY", origin=(x, y, z0))
            .box(l, w, h, centered=(True, True, False))
        )
        out = b if out is None else out.union(b)
    return out


def battery():
    """One pack in the aft bay, or two in the belly flanks.  See params."""
    return _boxes(P.BATTERY_PACKS, P.BATTERY_L, P.BATTERY_W, P.BATTERY_H, P.BATTERY_Z0)


def electronics():
    """Compute, DC-DC and the stop circuit, in the side bays.

    These used to be a lump in the mass table with no geometry, hanging under
    the deck.  Down here they sit 180 mm lower and get checked for clashes
    like everything else.
    """
    return _boxes(P.ELEC_PACKS, P.ELEC_L, P.ELEC_W, P.ELEC_H, P.ELEC_Z0)


def drivers():
    """One DM6540 per corner, flat on the inboard face of the nearest spine.

    Keeping them beside their own motor keeps the three phase leads short,
    which matters more than tidy grouping at 86 A peak.
    """
    out = None
    for _, x, y in P.CORNERS:
        sy = 1.0 if y > 0 else -1.0
        brd = (
            cq.Workplane("XY", origin=(x * 0.8, sy * (P.SPINE_Y - P.SPINE_T / 2 - P.DRIVER_H / 2),
                                       P.SWEEP_CLEAR_Z + 30))
            .box(P.DRIVER_L, P.DRIVER_H, P.DRIVER_W, centered=(True, True, False))
        )
        out = brd if out is None else out.union(brd)
    return out


def chassis(with_shell=True):
    asm = cq.Assembly(name="stem_e_chassis")
    asm.add(frame(), name="frame", color=ALU)
    asm.add(battery(), name="battery", color=cq.Color(0.20, 0.20, 0.22))
    asm.add(drivers(), name="drivers", color=cq.Color(0.10, 0.39, 0.10))
    asm.add(electronics(), name="electronics", color=cq.Color(0.33, 0.30, 0.36))
    if with_shell:
        for nm, col in (("shell_skirt", (0.17, 0.18, 0.19)),
                        ("shell_upper", (0.90, 0.91, 0.89)),
                        ("shell_belt", (0.08, 0.09, 0.09)),
                        ("shell_cover", (0.14, 0.15, 0.16)),
                        ("shell_panels", (0.23, 0.25, 0.27)),
                        ("shell_light", (0.93, 0.95, 1.00)),
                        ("estop", (0.72, 0.16, 0.08))):
            asm.add(globals()[nm](), name=nm, color=cq.Color(*col))
    for name, x, y in P.CORNERS:
        asm.add(
            corner_module(name, mirror=(y < 0)),
            name="module_" + name,
            loc=cq.Location(cq.Vector(x, y, 0)),
        )
    return asm
