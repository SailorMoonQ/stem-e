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
G_ALU = 26000.0              # MPa, shear
ALU_SHEAR_YIELD = 165.0      # MPa, 6061-T6
RAIL_BOLT_D = 3.0            # MGN12 takes M3
RAIL_BOLT_PITCH = 25.0       # MGN12 hole pitch
G = 9.81
ARM_MOMENT_NM = 75.0         # both arms extended, payload at ARM_REACH_FWD
HAND_HEIGHT_MM = 1400.0


def _vol(s):
    return s.val().Volume()


def members():
    """The frame piece by piece, straight from the model.

    This used to re-declare the whole frame by hand and had drifted badly:
    the cross members were still at +-280 after the model moved them to
    CROSS_X, and the lower spine was 500 long against 524.  Stiffness
    conclusions were being drawn about a frame nobody was building.
    """
    return model.frame_members()


# The moment arrives in the deck over the doubler, so that is the footprint.
COLUMN_FOOT = P.COLUMN_DOUBLER


def box_section():
    """Second moment of the frame as a closed box, bending fore and aft.

    Idealised: deck and base plate as flanges, the two side spines as webs.
    This is what actually resists the column's base moment globally, and it is
    the number that says whether the long members are oversized.
    """
    z_deck = P.TOP_PLATE_Z0 + P.TOP_PLATE_T / 2
    z_base = P.BASE_PLATE_Z0 + P.BASE_PLATE_T / 2
    a_deck = P.DECK_W * P.TOP_PLATE_T
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


def box_torsion():
    """Twist of the same closed box, Bredt thin walled section.

    Bending alone does not settle whether the long members are oversized: an
    arm reaching sideways, or one wheel on a bump, twists the frame rather
    than bending it.  The webs are perforated, which Bredt does not model, so
    the real figure is worse than this; it is here to show the order.
    """
    h = P.TOP_PLATE_Z0 - P.BASE_PLATE_Z0
    b = 2 * P.SPINE_Y
    area = b * h
    perim = (b / P.TOP_PLATE_T + b / P.BASE_PLATE_T
             + 2 * h / P.SPINE_T)
    j = 4 * area ** 2 / perim
    theta = ARM_MOMENT_NM * 1000.0 * P.WHEELBASE / (G_ALU * j)
    return {"J": j, "hand_mm": theta * HAND_HEIGHT_MM}


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


def local_checks(spine_t=None):
    """What actually sizes the side spine, as opposed to global stiffness.

    The box is two to three orders over on both bending and torsion, so the
    8 mm web is not there for the column moment.  Three local paths were
    missing from this budget and are the candidates: the rail screws' thread
    engagement, bearing at those holes, and shear buckling of the web.
    """
    t = P.SPINE_T if spine_t is None else spine_t
    out = {}

    # The corner module hangs off two rails on the outer face of the spine.
    # Traction at the contact patch is reacted as a couple across the rail
    # pitch, and that is what tries to pull a rail off the web - far more than
    # the corner's share of the weight.
    f_trac = P.F_TRACTIVE_PEAK / 4.0
    moment = f_trac * (P.RAIL_Z0 + P.RAIL_LEN / 2.0)        # N.mm about Y
    per_rail = moment / P.RAIL_PITCH_X                      # N, tension on one
    n_bolt = int(P.RAIL_LEN // RAIL_BOLT_PITCH) + 1
    bolt_tension = per_rail / n_bolt

    # Thread stripping in the tapped web.  0.75 x pi x D x Le is the usual
    # engineering estimate of internal thread shear area.
    engage = t                                              # tapped right through
    strip_area = 0.75 * math.pi * RAIL_BOLT_D * engage
    out["thread"] = (bolt_tension, strip_area * ALU_SHEAR_YIELD,
                     "M%.0f x %.1f mm 啮合" % (RAIL_BOLT_D, engage))

    # Bearing at the same holes, from the corner's vertical share carried in
    # shear along the rail.
    corner_n = (massprops.chassis_mass_properties()[0]
                + P.UPPER_BODY_MASS + P.PAYLOAD_MASS) * G / 4.0
    bearing = corner_n / (2 * n_bolt * RAIL_BOLT_D * t)
    out["bearing"] = (bearing, ALU_SHEAR_YIELD, "孔壁承压")

    # Shear buckling of the web.  The truss holes cut it into ligaments, and
    # the ligament width, not the full height, is the panel that buckles.
    b = min(P.WEB_HOLE_PITCH - P.WEB_HOLE_D,
            P.TOP_PLATE_Z0 - P.SWEEP_CLEAR_Z)
    tau_cr = 5.35 * math.pi ** 2 * E_ALU / (12 * (1 - 0.33 ** 2)) * (t / b) ** 2
    shear = ARM_MOMENT_NM * 1000.0 / P.WHEELBASE / (
        2 * (P.TOP_PLATE_Z0 - P.SWEEP_CLEAR_Z) * t)
    out["buckling"] = (shear, min(tau_cr, ALU_SHEAR_YIELD),
                       "腹板剪切，筋宽 %.0f mm" % b)
    return out


def yoke_checks():
    """What sizes the steering yoke, the plate the hub motor bolts to.

    It is the heaviest unlightened machined part on the machine and it swings
    with the steering, so it is worth knowing whether any of its 16 mm is
    doing work.  Three cases: the corner's weight, traction at the contact
    patch, and the moment from hanging the wheel off a single sided flange.
    """
    corner_n = (massprops.chassis_mass_properties()[0]
                + P.UPPER_BODY_MASS + P.PAYLOAD_MASS) * G / 4.0
    f_trac = P.F_TRACTIVE_PEAK / 4.0
    w, t = 90.0, P.YOKE_PLATE_T
    h = P.YOKE_TOP_Z1 - 37.5

    # Weight: straight compression down the web.
    out = [("角载荷压应力", corner_n / (w * t))]

    # Traction at the contact patch, reacted at the top plate.  In plane
    # bending of the web, which is the direction it is strong in.
    m_trac = f_trac * P.YOKE_TOP_Z0
    out.append(("牵引力矩，面内弯曲", m_trac * (w / 2) / (t * w ** 3 / 12.0)))

    # The wheel hangs off one flange, so the corner load acts a flange offset
    # out of the web's plane.  This is the weak direction.
    m_off = corner_n * P.HUB_FLANGE_OFFSET
    out.append(("单边法兰偏置，面外弯曲", m_off * (t / 2) / (w * t ** 3 / 12.0)))
    return out, corner_n, f_trac


def base_plate_checks(t=None):
    """What sizes the base plate, which carries the battery and the electronics.

    Assumes they are through bolted with nuts rather than tapped into the
    plate.  That is not a free choice: a proper tapped thread wants two
    diameters, so 6 mm was never enough for the M5 or M6 an 8 kg pack
    deserves, and the belly pan comes off, so the underside is reachable.
    """
    t = P.BASE_PLATE_T if t is None else t
    out = []

    # Bending of the tray under the pack, spanning between the two spines.
    span = 2 * P.SPINE_Y
    w = P.BATTERY_MASS * G / P.BATTERY_L           # N/mm along the span
    inertia = P.BATTERY_L * t ** 3 / 12.0
    out.append(("电池下板弯 mm", 5 * w * span ** 4 / (384 * E_ALU * inertia), 0.5))

    # Washer bearing at one mounting bolt, 4 points, 4 g shock.
    bolt_n = P.BATTERY_MASS * G * 4.0 / 4.0
    washer = math.pi / 4 * (12.5 ** 2 - 6.5 ** 2)
    out.append(("螺栓垫圈承压 MPa", bolt_n / washer, 276.0))

    # The ligament left between lightening holes, as a strip in bending.
    lig = P.LIGHTEN_PITCH - P.LIGHTEN_D
    out.append(("减重孔间筋 宽/厚", lig / t, 6.0))
    return out


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
    t = box_torsion()
    print("  整体箱形扭转 J = %.3e mm4 -> 手端 %.3f mm（腹板开孔未计入，实际更差）"
          % (t["J"], t["hand_mm"]))
    print("  结论：弯和扭都过剩两到三个数量级，长构件是减重的主要目标。")
    print("        但本脚本只算整体刚度，没有算导轨螺纹啮合、局部承压和腹板失稳，")
    print("        立板厚度很可能是被那些局部载荷定下来的 —— 减薄前必须先补上。")
    print("\n  但力矩要先从柱底传到立板和横梁，这一段是甲板的局部板弯。")
    print("  梁条模型对两端固支的板是偏保守的，下面当量级看，不当结论：")
    free = 2 * P.CROSS_X - COLUMN_FOOT
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

    print()
    print("底板（穿螺栓加螺母，不攻丝）")
    print("  %-22s %10s %10s %8s" % ("", "作用", "许用", "利用率"))
    for t in (P.BASE_PLATE_T, 5.0, 4.0, 3.0):
        row = base_plate_checks(t)
        worst = max(a / c for _, a, c in row)
        print("  t = %.0f mm  ->  最大利用率 %.0f%%%s" % (
            t, 100 * worst, "" if worst < 1 else "   超了"))
        for label, act, cap in row:
            print("    %-22s %10.2f %10.2f %7.0f%%" % (label, act, cap, 100 * act / cap))

    print()
    print("转向摇臂（%.0f cm3 x4，最重的未减重机加件）" % (
        _vol(model.steering_yoke()) / 1000.0))
    rows, corner_n, f_trac = yoke_checks()
    print("  角载荷 %.0f N，单轮牵引峰值 %.0f N，6061-T6 屈服 276 MPa" % (corner_n, f_trac))
    for label, stress in rows:
        print("    %-24s %8.2f MPa   利用率 %4.1f%%" % (label, stress, 100 * stress / 276.0))

    print()
    print("立板局部校核（整体刚度之外的三条路径）")
    print("  %-26s %10s %10s %8s" % ("", "作用", "许用", "利用率"))
    for t in (P.SPINE_T, 6.0, 4.0, 3.0):
        c = local_checks(t)
        worst = max(v[0] / v[1] for v in c.values())
        print("  t = %.0f mm" % t)
        for k in ("thread", "bearing", "buckling"):
            act, cap, label = c[k]
            print("    %-24s %10.1f %10.1f %7.1f%%" % (label, act, cap, 100 * act / cap))
        print("    -> 最大利用率 %.1f%%%s" % (100 * worst,
                                        "" if worst < 1 else "   超了"))


if __name__ == "__main__":
    main()
