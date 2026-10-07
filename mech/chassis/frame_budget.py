"""Where the frame mass sits, and how stiff each piece actually needs to be.

    python frame_budget.py

The frame is sized by stiffness, not strength: this chassis is a manipulator
base, so what matters is how far the hand moves when the arms reach out, not
whether anything yields.  This script reports the mass of each member and the
deflection each one contributes, so thinning decisions are made against a
number instead of a feeling.
"""

import math

import cadquery as cq

import massprops
import model
import params as P

E_ALU = 69000.0              # MPa
G = 9.81
ARM_MOMENT_NM = 75.0         # both arms extended, payload at ARM_REACH_FWD
HAND_HEIGHT_MM = 1400.0


def _vol(s):
    return s.val().Volume()


def members():
    """Rebuild the frame piece by piece so each one can be weighed."""
    sweep = model._sweep_clearance()
    out = []

    base = (
        cq.Workplane("XY", origin=(0, 0, P.BASE_PLATE_Z0))
        .box(P.BASE_PLATE_L, P.BASE_PLATE_W, P.BASE_PLATE_T, centered=(True, True, False))
    )
    base = model._lighten(
        base, P.BASE_PLATE_Z0, P.BASE_PLATE_T, P.BASE_PLATE_L / 2, P.BASE_PLATE_W / 2,
        keepouts=[
            (-P.BATTERY_L / 2 - 20, P.BATTERY_L / 2 + 20, -P.BATTERY_W / 2 - 20, P.BATTERY_W / 2 + 20),
            (-310, -130, -P.SPINE_Y, P.SPINE_Y),
            (130, 310, -P.SPINE_Y, P.SPINE_Y),
        ],
    )
    out.append(("base plate %.0fx%.0f t%.0f" % (P.BASE_PLATE_L, P.BASE_PLATE_W, P.BASE_PLATE_T),
                base.cut(sweep)))

    top_l, top_w = P.BODY_L - 40, P.BODY_W - 160
    top = (
        cq.Workplane("XY", origin=(0, 0, P.TOP_PLATE_Z0))
        .box(top_l, top_w, P.TOP_PLATE_T, centered=(True, True, False))
    )
    top = model._lighten(top, P.TOP_PLATE_Z0, P.TOP_PLATE_T, top_l / 2, top_w / 2,
                         keepouts=[(-150, 150, -150, 150)])
    out.append(("deck %.0fx%.0f t%.0f" % (top_l, top_w, P.TOP_PLATE_T), top.cut(sweep)))

    spines = None
    for sy in (1.0, -1.0):
        y = sy * P.SPINE_Y
        s = (
            cq.Workplane("XY", origin=(0, y, P.SWEEP_CLEAR_Z))
            .box(P.BODY_L - 80, P.SPINE_T, P.TOP_PLATE_Z0 - P.SWEEP_CLEAR_Z,
                 centered=(True, True, False))
        )
        s = s.union(
            cq.Workplane("XY", origin=(0, y, P.BASE_PLATE_Z0 + P.BASE_PLATE_T))
            .box(500, P.SPINE_T, P.SWEEP_CLEAR_Z - P.BASE_PLATE_Z0 - P.BASE_PLATE_T,
                 centered=(True, True, False))
        )
        s = model._truss(s, "Y", y, (P.SWEEP_CLEAR_Z + P.TOP_PLATE_Z0) / 2,
                         (P.BODY_L - 80) / 2, exclude_abs=270.0)
        s = model._truss(s, "Y", y, P.BASE_PLATE_Z0 + 50, 250.0, exclude_abs=0.0)
        spines = s if spines is None else spines.union(s)
    out.append(("side spines x2 t%.0f" % P.SPINE_T, spines.cut(sweep)))

    cross = None
    for sx in (1.0, -1.0):
        c = (
            cq.Workplane("XY", origin=(sx * 280, 0, P.BASE_PLATE_Z0 + P.BASE_PLATE_T))
            .box(P.SPINE_T, 2 * P.SPINE_Y, P.TOP_PLATE_Z0 - P.BASE_PLATE_Z0 - P.BASE_PLATE_T,
                 centered=(True, True, False))
        )
        c = model._truss(c, "X", sx * 280, (P.BASE_PLATE_Z0 + P.TOP_PLATE_Z0) / 2,
                         P.SPINE_Y, exclude_abs=0.0)
        cross = c if cross is None else cross.union(c)
    out.append(("cross members x2 t%.0f" % P.SPINE_T, cross.cut(sweep)))
    return out


COLUMN_FOOT = 300.0          # lift column interface footprint on the deck


def box_section():
    """Second moment of the frame as a closed box, bending fore and aft.

    Idealised: deck and base plate as flanges, the two side spines as webs.
    This is what actually resists the column's base moment globally, and it is
    the number that says whether the long members are oversized.
    """
    z_deck = P.TOP_PLATE_Z0 + P.TOP_PLATE_T / 2
    z_base = P.BASE_PLATE_Z0 + P.BASE_PLATE_T / 2
    a_deck = (P.BODY_W - 160) * P.TOP_PLATE_T
    a_base = P.BASE_PLATE_W * P.BASE_PLATE_T
    h_web = P.TOP_PLATE_Z0 - (P.BASE_PLATE_Z0 + P.BASE_PLATE_T)
    z_web = (P.TOP_PLATE_Z0 + P.BASE_PLATE_Z0 + P.BASE_PLATE_T) / 2
    a_web = 2 * P.SPINE_T * h_web

    area = a_deck + a_base + a_web
    na = (a_deck * z_deck + a_base * z_base + a_web * z_web) / area
    inertia = (
        a_deck * (z_deck - na) ** 2
        + a_base * (z_base - na) ** 2
        + 2 * P.SPINE_T * h_web ** 3 / 12.0
        + a_web * (z_web - na) ** 2
    )
    theta = ARM_MOMENT_NM * 1000.0 * P.WHEELBASE / (2.0 * E_ALU * inertia)
    return {"I": inertia, "na": na, "hand_mm": theta * HAND_HEIGHT_MM}


def deck_local(t=None, span=None):
    """Local plate bending of the deck right under the lift column.

    The box above only applies once the moment has reached the spines and cross
    members.  Getting it there is plate bending in a bare sheet, and that is the
    weak link.  A beam strip is a crude stand in for a plate; treat it as an
    order of magnitude, not a result.
    """
    t = P.TOP_PLATE_T if t is None else t
    span = (2 * 280.0 - COLUMN_FOOT) if span is None else span
    inertia = COLUMN_FOOT * t ** 3 / 12.0
    theta = ARM_MOMENT_NM * 1000.0 * span / (2.0 * E_ALU * inertia)
    return theta * HAND_HEIGHT_MM


def main():
    rows = members()
    total = 0.0
    print("%-34s %12s %9s" % ("构件", "体积 cm3", "质量 kg"))
    for name, solid in rows:
        v = _vol(solid)
        m = v * P.ALU_DENSITY
        total += m
        print("%-34s %12.1f %9.2f" % (name, v / 1000.0, m))
    print("%-34s %12s %9.2f" % ("合计", "", total))
    print("%-34s %12s %9.2f" % ("model.frame() 实际", "", _vol(model.frame()) * P.ALU_DENSITY))

    curb = massprops.chassis_mass_properties()[0]
    print("\n车架占底盘整备质量 %.0f%%" % (total / curb * 100))

    b = box_section()
    print("\n升降柱底部 %.0f Nm 力矩下的手端漂移（参照：悬挂本身约 5 mm）" % ARM_MOMENT_NM)
    print("  整体箱形截面 I = %.3e mm4，中性轴 z = %.0f -> 手端 %.3f mm"
          % (b["I"], b["na"], b["hand_mm"]))
    print("  结论：长构件（立板、横梁）远远过剩，是减重的主要目标")
    print("\n  但力矩要先从柱底传到立板和横梁，这一段是甲板的局部板弯。")
    print("  梁条模型对两端固支的板是偏保守的，下面当量级看，不当结论：")
    free = 2 * (P.CROSS_X - 115.0)
    cases = [
        ("横梁在 ±280，甲板 6 mm，无加强", 6.0, 2 * 280.0 - COLUMN_FOOT),
        ("横梁移到 ±%.0f，甲板 6 mm" % P.CROSS_X, 6.0, free),
        ("再加 %.0f mm 加强板，局部 %.0f mm"
         % (P.COLUMN_DOUBLER_T, P.TOP_PLATE_T + P.COLUMN_DOUBLER_T),
         P.TOP_PLATE_T + P.COLUMN_DOUBLER_T, free),
    ]
    for label, t, span in cases:
        print("    %-32s -> 手端 %6.2f mm" % (label, deck_local(t, span)))
    print("  方向确认了，定稿前仍需 FEA 复核")


if __name__ == "__main__":
    main()
