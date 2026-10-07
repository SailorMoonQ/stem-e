"""Error budget for the four corner load cells.

    python error_budget.py

Answers one question: how accurately can this chassis know its own centre of
gravity and its payload mass, and what actually limits that.

Three load paths are compared:

  offset     spring and cell inboard of the kingpin at SUSP_SPRING_Y.  The
             offset puts a moment on the rail carriages, and that normal load
             is what makes them stick.
  symmetric  two springs and two cells straddling the kingpin at y = 0, so the
             rails carry no moment from the suspension at all.
  flexure    no rails.  A CNC parallelogram flexure with self bonded strain
             gauges: no friction, but DIY gauge accuracy instead of a
             calibrated commercial cell.

Every assumption is a named constant.  Change one and rerun.
"""

import math

import massprops
import params as P

G = 9.81

# Linear guide assumptions, MGN12H class
MU_BALL = 0.005              # rolling friction coefficient
SEAL_DRAG_N = 1.0            # per carriage, dominant term at low load
CARRIAGE_LEVER_M = 0.030     # effective lever reacting a pitch moment
N_CARRIAGE = 2               # per corner

# Load cell accuracy, fraction of full scale
FS_N = P.LOADCELL_RANGE_KG * G
ACC_COMMERCIAL = 0.0005      # 0.05 % FS, ordinary C3 single point cell
ACC_DIY_GAUGE = 0.005        # 0.5 % FS, hand bonded foil gauges, realistic

MODULE_MASS_KG = 6.2         # wheel, yoke, tube, housing, actuator, bracket
MODULE_COG_Y_M = 0.010       # module centre of gravity offset from the kingpin


def rail_friction(spring_offset_m):
    """Stiction band at one corner, newtons."""
    curb, _, _ = massprops.chassis_mass_properties()
    total_n = (curb + P.UPPER_BODY_MASS + P.PAYLOAD_MASS) * G
    corner_n = total_n / 4.0
    spring_n = corner_n - MODULE_MASS_KG * G
    moment = spring_n * spring_offset_m + MODULE_MASS_KG * G * MODULE_COG_Y_M
    normal = moment / (N_CARRIAGE * CARRIAGE_LEVER_M)
    return N_CARRIAGE * (MU_BALL * normal + SEAL_DRAG_N), spring_n, moment


def budget(label, friction_n, cell_accuracy):
    """Propagate per corner force error into CoG position and payload mass."""
    curb, _, _ = massprops.chassis_mass_properties()
    total_n = (curb + P.UPPER_BODY_MASS + P.PAYLOAD_MASS) * G
    eps = math.hypot(friction_n, cell_accuracy * FS_N)      # per corner, newtons
    combined = 2.0 * eps                                     # rss of four corners
    cog_x_mm = combined / total_n * (P.WHEELBASE / 2)
    cog_y_mm = combined / total_n * (P.TRACK / 2)
    payload_kg = combined / G
    return {
        "label": label,
        "friction_n": friction_n,
        "cell_err_n": cell_accuracy * FS_N,
        "eps_n": eps,
        "cog_x_mm": cog_x_mm,
        "cog_y_mm": cog_y_mm,
        "payload_kg": payload_kg,
    }


def main():
    curb, cog_z, _ = massprops.chassis_mass_properties()
    total = curb + P.UPPER_BODY_MASS + P.PAYLOAD_MASS
    print("整车 %.1f kg，单角静载 %.0f N，传感器量程 %.0f N" % (total, total * G / 4, FS_N))

    f_off, spring_n, moment = rail_friction(abs(P.SUSP_SPRING_Y) / 1000.0)
    f_sym, _, moment_sym = rail_friction(0.0)
    print("\n导轨摩擦")
    print("  弹簧偏置 %.0f mm：弹簧力 %.0f N，力矩 %.1f Nm，滑块法向力 %.0f N，"
          "静摩擦带 ±%.2f N"
          % (abs(P.SUSP_SPRING_Y), spring_n, moment,
             moment / (N_CARRIAGE * CARRIAGE_LEVER_M), f_off))
    print("  弹簧对称布置：力矩 %.2f Nm，静摩擦带 ±%.2f N（基本只剩密封阻力）"
          % (moment_sym, f_sym))
    print("  改善倍数 %.1fx" % (f_off / f_sym))

    cases = [
        budget("A 导轨 + 偏置弹簧 + 商用传感器", f_off, ACC_COMMERCIAL),
        budget("B 导轨 + 对称弹簧 + 商用传感器", f_sym, ACC_COMMERCIAL),
        budget("C 柔性铰链 + 自贴应变片", 0.0, ACC_DIY_GAUGE),
        budget("D 柔性铰链 + 商用级精度（参照）", 0.0, ACC_COMMERCIAL),
    ]
    print("\n%-30s %9s %9s %10s %10s %10s"
          % ("方案", "摩擦 N", "传感 N", "合成 N", "重心 mm", "负载 kg"))
    for c in cases:
        print("%-30s %9.2f %9.2f %10.2f %10.2f %10.2f"
              % (c["label"], c["friction_n"], c["cell_err_n"], c["eps_n"],
                 c["cog_x_mm"], c["payload_kg"]))

    print("\n对照：防倾覆判据需要的分辨率")
    print("  前向可用力臂 %.0f mm，需求 %.0f mm，余量 %.0f mm"
          % (P.WHEELBASE / 2, 176.9, P.WHEELBASE / 2 - 176.9))
    print("  即重心估计误差只要远小于 %.0f mm 就不影响安全判断" % (P.WHEELBASE / 2 - 176.9))
    print("  额定负载 %.0f kg，方案 B 的称重误差占 %.0f%%"
          % (P.PAYLOAD_MASS, cases[1]["payload_kg"] / P.PAYLOAD_MASS * 100))


if __name__ == "__main__":
    main()
