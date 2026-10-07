"""Compare this chassis with the AgileX Ranger Air on the same load case.

    python compare_ranger.py

The point is not a feature table.  It is this: run the STEM-E upper body, the
same 40 kg at 1.4 m reaching 0.7 m forward, on both footprints and see what
tipping margin each one leaves.  Ranger Air numbers are from the vendor page,
https://www.agilex.ai/products/ranger-air, and are stated, not measured here.

Anything the vendor does not publish is left out rather than guessed.
"""

import math

import massprops
import params as P

G = 9.81
ARM_MASS = 12.0

RANGER_AIR = {
    "name": "AgileX Ranger Air",
    "body_l": 552.0,
    "body_w": 500.0,
    "body_h": 250.0,
    "wheelbase": 388.0,
    "track": 338.0,
    "ground_clearance": 45.0,
    "curb_kg": 53.0,
    "curb_cog_mm": 125.0,          # assumed: half the 250 mm body height, battery low
    "rated_payload_kg": 80.0,
    "speed_ms": 1.5,
    "grade_deg": 8.0,
    "ingress": "IP22",
}


def tipping(curb_kg, curb_cog_mm, wheelbase, track):
    """Margin left over when the STEM-E upper body sits on this footprint."""
    total = curb_kg + P.UPPER_BODY_MASS + P.PAYLOAD_MASS
    column_head = P.UPPER_BODY_MASS - ARM_MASS
    cog_z = (
        curb_kg * curb_cog_mm
        + column_head * P.UPPER_BODY_COG_Z
        + ARM_MASS * 1200.0
        + P.PAYLOAD_MASS * P.PAYLOAD_Z
    ) / total
    slope = cog_z * math.tan(math.radians(P.FLOOR_SLOPE_DEG))
    fwd = (ARM_MASS * P.ARM_REACH_FWD / 2 + P.PAYLOAD_MASS * P.ARM_REACH_FWD) / total
    lat = (ARM_MASS * P.ARM_REACH_LAT / 2 + P.PAYLOAD_MASS * P.ARM_REACH_LAT) / total
    fwd_need = fwd + cog_z * P.ESTOP_DECEL / G + slope
    lat_need = lat + cog_z * P.LATERAL_ACCEL / G + slope
    return {
        "total_kg": total,
        "cog_z": cog_z,
        "fwd_need": fwd_need,
        "lat_need": lat_need,
        "fwd_sf": (wheelbase / 2) / fwd_need,
        "lat_sf": (track / 2) / lat_need,
    }


def main():
    curb, curb_z, _, _ = massprops.chassis_mass_properties()
    mine = tipping(curb, curb_z, P.WHEELBASE, P.TRACK)
    ra = tipping(RANGER_AIR["curb_kg"], RANGER_AIR["curb_cog_mm"],
                 RANGER_AIR["wheelbase"], RANGER_AIR["track"])

    rows = [
        ("车体 长x宽x高 mm", "%.0f x %.0f x %.0f" % (RANGER_AIR["body_l"], RANGER_AIR["body_w"],
                                                 RANGER_AIR["body_h"]),
         "%.0f x %.0f x %.0f" % (P.BODY_L, P.BODY_W, P.DECK_Z)),
        ("车体体积 L", "%.0f" % (RANGER_AIR["body_l"] * RANGER_AIR["body_w"]
                              * RANGER_AIR["body_h"] / 1e6),
         "%.0f" % (P.BODY_L * P.BODY_W * P.DECK_Z / 1e6)),
        ("轴距 x 轮距 mm", "%.0f x %.0f" % (RANGER_AIR["wheelbase"], RANGER_AIR["track"]),
         "%.0f x %.0f" % (P.WHEELBASE, P.TRACK)),
        ("离地间隙 mm", "%.0f" % RANGER_AIR["ground_clearance"], "%.0f" % P.GROUND_CLEARANCE),
        ("整备质量 kg", "%.0f" % RANGER_AIR["curb_kg"], "%.1f" % curb),
        ("整备密度 kg/m3", "%.0f" % (RANGER_AIR["curb_kg"] /
                                 (RANGER_AIR["body_l"] * RANGER_AIR["body_w"]
                                  * RANGER_AIR["body_h"] / 1e9)),
         "%.0f" % (curb / (P.BODY_L * P.BODY_W * P.DECK_Z / 1e9))),
        ("额定载重 kg", "%.0f" % RANGER_AIR["rated_payload_kg"],
         "%.0f（上半身 %.0f + 负载 %.0f）" % (P.UPPER_BODY_MASS + P.PAYLOAD_MASS,
                                        P.UPPER_BODY_MASS, P.PAYLOAD_MASS)),
        ("额定车速 m/s", "%.2f" % RANGER_AIR["speed_ms"], "%.2f" % P.V_RATED),
        ("防护等级", RANGER_AIR["ingress"], "无"),
        ("悬挂", "厂商未公布", "滑柱式独立 ±%.0f mm，%.0f N/mm"
         % (P.SUSP_TRAVEL_NOMINAL, P.SUSP_RATE)),
        ("重心可观测", "无", "四角称重，直接解算"),
    ]
    width = max(len(r[0]) for r in rows)
    print("%-*s  %-28s  %s" % (width, "项目", RANGER_AIR["name"], "STEM-E 底盘 v1"))
    print("-" * (width + 62))
    for k, a, b in rows:
        print("%-*s  %-28s  %s" % (width, k, a, b))

    print("\n同一载荷工况下的倾覆安全系数")
    print("  上半身 %.0f kg @ 1.4 m，前伸 %.0f mm，手持 %.0f kg，"
          "急停 %.1f m/s2，地面 %.0f 度"
          % (P.UPPER_BODY_MASS, P.ARM_REACH_FWD, P.PAYLOAD_MASS,
             P.ESTOP_DECEL, P.FLOOR_SLOPE_DEG))
    print("%-18s %10s %10s" % ("", RANGER_AIR["name"], "STEM-E v1"))
    for key, label in (("total_kg", "整车总质量 kg"), ("cog_z", "整车质心高 mm"),
                       ("fwd_need", "前向需求力臂 mm"), ("lat_need", "侧向需求力臂 mm")):
        print("%-18s %10.1f %10.1f" % (label, ra[key], mine[key]))
    print("%-18s %10.1f %10.1f" % ("可用前向力臂 mm", RANGER_AIR["wheelbase"] / 2,
                                P.WHEELBASE / 2))
    print("%-18s %10.1f %10.1f" % ("可用侧向力臂 mm", RANGER_AIR["track"] / 2, P.TRACK / 2))
    print("%-18s %10.2f %10.2f" % ("前倾安全系数", ra["fwd_sf"], mine["fwd_sf"]))
    print("%-18s %10.2f %10.2f" % ("侧倾安全系数", ra["lat_sf"], mine["lat_sf"]))

    print("\n反过来：把 Ranger Air 的额定 80 kg 货物放到两台车上")
    print("  Ranger Air 额定 %.0f kg；STEM-E 底盘按 %.0f N 额定牵引力，"
          % (RANGER_AIR["rated_payload_kg"], P.F_TRACTIVE_RATED))
    for label, mass in (("Ranger Air 满载", RANGER_AIR["curb_kg"] + 80.0),
                        ("STEM-E 满载", curb + P.UPPER_BODY_MASS + P.PAYLOAD_MASS)):
        grade = math.degrees(math.asin(min(1.0, P.F_TRACTIVE_RATED / (mass * G))))
        print("  %-16s %6.1f kg  本车额定牵引力下可爬 %.1f 度" % (label, mass, grade))


if __name__ == "__main__":
    main()
