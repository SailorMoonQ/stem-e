"""Solve the footprint backwards from the duty the robot actually has to do.

    python sizing.py

The current 700 x 500 came from one duty case.  Change the payload, the reach
or the emergency deceleration and the required footprint moves, which moves the
body, the frame mass and how the wheels sit against the body.  This solves that
loop instead of guessing at it.

Chassis mass is scaled from the built model rather than re-run per candidate:
plates scale with body area, webs with body length and width, and everything
else (motors, battery, bearings, wiring) is fixed.  Good to a few percent,
which is well inside the precision of the duty assumptions themselves.
"""

import math

import params as P

G = 9.81
SF_TARGET = 2.0
SWEEP = P.WHEEL_SWEEP_OD             # body is always footprint plus this
ARM_MASS = P.ARM_MASS
UPPER_COG_Z = P.UPPER_BODY_COG_Z

# Reference point: what the built model weighs at its current size.
REF_L, REF_W = 880.0, 680.0
REF_PLATES = 9.3                     # deck plus base plate, scales with area
REF_SPINES = 5.78                    # scales with body length
REF_CROSS = 3.58                     # scales with body width
REF_LOCAL = 0.4                      # column doubler and pads, fixed
REF_SHELL = 1.96                     # scales with perimeter
FIXED_KG = 40.0                      # motors, battery, bearings, rails, wiring
CHASSIS_COG_Z = 194.0


def chassis_mass(body_l, body_w):
    frame = (
        REF_PLATES * (body_l * body_w) / (REF_L * REF_W)
        + REF_SPINES * body_l / REF_L
        + REF_CROSS * body_w / REF_W
        + REF_LOCAL
    )
    shell = REF_SHELL * (body_l + body_w) / (REF_L + REF_W)
    return FIXED_KG + frame + shell, frame, shell


def solve(upper_kg=P.UPPER_BODY_MASS, payload_kg=P.PAYLOAD_MASS,
          reach_fwd=P.ARM_REACH_FWD, reach_lat=P.LAT_DESIGN_REACH,
          payload_z=P.PAYLOAD_Z, upper_cog_z=P.UPPER_BODY_COG_Z,
          estop=P.ESTOP_DECEL, lateral=P.LATERAL_ACCEL, sf=SF_TARGET):
    """Iterate footprint and chassis mass until they agree."""
    body_l, body_w = REF_L, REF_W
    for _ in range(40):
        curb, _, _ = chassis_mass(body_l, body_w)
        total = curb + upper_kg + payload_kg
        cog_z = (curb * CHASSIS_COG_Z + upper_kg * upper_cog_z
                 + payload_kg * payload_z) / total
        cog_x = curb * (P.BATTERY_X * body_l / REF_L) * (8.0 / curb) / total * curb / curb
        # battery is the only deliberate fore and aft offset
        cog_x = 8.0 * (P.BATTERY_X * body_l / REF_L) / total
        slope = cog_z * math.tan(math.radians(P.FLOOR_SLOPE_DEG))

        fwd = (cog_x * total + ARM_MASS * reach_fwd / 2
               + payload_kg * reach_fwd) / total + cog_z * estop / G + slope
        lat = (ARM_MASS * P.LAT_ARM_FRACTION * reach_lat / 2
               + payload_kg * reach_lat) / total + cog_z * lateral / G + slope

        wb, tr = 2 * sf * fwd, 2 * sf * lat
        new_l, new_w = wb + SWEEP, tr + SWEEP
        if abs(new_l - body_l) < 0.5 and abs(new_w - body_w) < 0.5:
            body_l, body_w = new_l, new_w
            break
        body_l, body_w = new_l, new_w

    curb, frame, shell = chassis_mass(body_l, body_w)
    return {
        "wheelbase": body_l - SWEEP,
        "track": body_w - SWEEP,
        "body_l": body_l,
        "body_w": body_w,
        "curb": curb,
        "frame": frame,
        "total": curb + upper_kg + payload_kg,
        "cog_z": cog_z,
        "wheel_over_len": P.HUB_TIRE_OD / body_l,
        "height_over_wheel": P.DECK_Z / P.HUB_TIRE_OD,
    }


def equipment_bay(body_l, body_w):
    """Usable bay between a cross member and the body end.

    The battery has not been bought, so this is a procurement constraint rather
    than a blocker: pick a pack that fits this box, or split it in two.
    """
    cross = P.COLUMN_PCD / 2 + 25.0 + P.SPINE_T / 2
    # spines sit inboard of the rails, which sit inboard of the bearing housing
    spine_y = body_w / 2 - P.SWEEP_CLEAR_R - (P.TRACK / 2 - P.SPINE_Y)
    return body_l / 2 - 10.0 - cross, 2 * spine_y


# From params, so the study and the model cannot disagree about the criterion
# the width is derived from.  50 a side is the floor, not a comfortable value.
DOOR_MARGIN = P.DOOR_MARGIN
DOOR_CLEAR = (P.DOOR_CLEAR, 800.0)   # 800 rough opening gives under 750 clear


def door_fit(body_w, clear):
    """4WS crabs through sideways, so the narrow side is what has to fit.

    What has to clear the frame is the widest point of the finished machine,
    not the structural width.  The bumper band stands SHELL_BELT_OUT proud on
    each side and was added to the design after this study was written, so
    this test was passing a number 12 mm narrower than the real one.
    """
    overall = body_w + 2 * P.SHELL_BELT_OUT
    return clear - overall, (clear - overall) / 2 >= DOOR_MARGIN


CASES = [
    ("已建 744 x 604", dict(_fixed=(P.WHEELBASE, P.TRACK))),
    ("同任务书按 SF 2.0 重解", {}),
    ("急停 1.0，其余不动", dict(estop=1.0, lateral=0.7)),
    ("--", None),
    ("急停 1.0 + 侧向工作范围 450 -> 350", dict(estop=1.0, lateral=0.7, reach_lat=350.0)),
    ("再把侧向加速度 0.7 -> 0.5", dict(estop=1.0, lateral=0.5, reach_lat=350.0)),
    ("再把侧向范围收到 300", dict(estop=1.0, lateral=0.5, reach_lat=300.0)),
    ("--", None),
    ("上面那组 + 负载 3kg", dict(estop=1.0, lateral=0.5, reach_lat=300.0, payload_kg=3.0)),
    ("上面那组 + 前伸 650", dict(estop=1.0, lateral=0.5, reach_lat=300.0,
                            payload_kg=3.0, reach_fwd=650.0)),
]


def main():
    print("%-34s %5s %5s %5s %5s %5s %5s   %-9s %-9s"
          % ("方案", "轴距", "轮距", "车长", "车宽", "整备", "车架",
             "净宽750", "净宽800"))
    print("%-34s %5s %5s %5s %5s %5s %5s   %-9s %-9s"
          % ("", "", "", "", "", "", "", "单边余量", "单边余量"))
    for label, kw in CASES:
        if kw is None:
            print("-" * 88)
            continue
        fixed = kw.pop("_fixed", None)
        r = solve(**kw)
        if fixed:
            r["wheelbase"], r["track"] = fixed
            r["body_l"], r["body_w"] = fixed[0] + SWEEP, fixed[1] + SWEEP
            r["curb"], r["frame"] = 60.9, 19.0
        bay_l, bay_w = equipment_bay(r["body_l"], r["body_w"])
        r["bay"] = (bay_l, bay_w)
        g650, ok650 = door_fit(r["body_w"], DOOR_CLEAR[0])
        g700, ok700 = door_fit(r["body_w"], DOOR_CLEAR[1])
        print("%-34s %5.0f %5.0f %5.0f %5.0f %5.1f %5.1f   %+5.0f %-3s %+5.0f %-3s"
              % (label, r["wheelbase"], r["track"], r["body_l"], r["body_w"],
                 r["curb"], r["frame"],
                 g650 / 2, "可" if ok650 else "不可",
                 g700 / 2, "可" if ok700 else "不可"))

    print("\n过门按 4WS 横移算，卡的是车宽；单边余量按 %.0f mm 判可行" % DOOR_MARGIN)
    print("转向扫掠固定占掉 %.0f mm，车宽下限 = 轮距 + %.0f" % (SWEEP, SWEEP))

    print("\n各方案的设备舱，前后各一个，电池按这个选型")
    for label, kw in CASES:
        if kw is None or "_fixed" in kw:
            continue
        r = solve(**kw)
        bl, bw = equipment_bay(r["body_l"], r["body_w"])
        print("  %-34s %5.0f x %5.0f mm" % (label, bl, bw))


if __name__ == "__main__":
    main()
