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
            (P.BATTERY_X - P.BATTERY_L / 2 - 20, P.BATTERY_X + P.BATTERY_L / 2 + 20,
             -P.BATTERY_W / 2 - 20, P.BATTERY_W / 2 + 20),
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


def shell():
    """Outer skin with open corner wheel arches."""
    h = P.DECK_Z - P.GROUND_CLEARANCE
    t = P.SHELL_T
    body = (
        cq.Workplane("XY", origin=(0, 0, P.GROUND_CLEARANCE))
        .box(P.BODY_L, P.BODY_W, h, centered=(True, True, False))
        .edges("|Z").fillet(30)
    )
    inner = (
        cq.Workplane("XY", origin=(0, 0, P.GROUND_CLEARANCE))
        .box(P.BODY_L - 2 * t, P.BODY_W - 2 * t, h, centered=(True, True, False))
        .edges("|Z").fillet(30 - t)
    )
    return body.cut(inner).cut(_sweep_clearance())


def battery():
    """Rear bay, outboard of the aft cross member and under a service opening."""
    return (
        cq.Workplane("XY", origin=(P.BATTERY_X, 0, P.BASE_PLATE_Z0 + P.BASE_PLATE_T))
        .box(P.BATTERY_L, P.BATTERY_W, P.BATTERY_H, centered=(True, True, False))
    )


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
    if with_shell:
        asm.add(shell(), name="shell", color=cq.Color(0.2, 0.45, 0.75, 0.35))
    for name, x, y in P.CORNERS:
        asm.add(
            corner_module(name, mirror=(y < 0)),
            name="module_" + name,
            loc=cq.Location(cq.Vector(x, y, 0)),
        )
    return asm
