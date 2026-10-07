"""Dimensioned general arrangement drawings, generated from ``params``.

    python drawing.py

Sheet 1  GA: plan, side elevation, end elevation, data block.
Sheet 2  Corner module section and the DM-H65 mounting interface.

Everything is drawn analytically from the parameter file rather than projected
from the solid, so a dimension can never drift away from the number the model
was built with.  Output lands in ``export/`` as PDF, SVG and PNG.
"""

import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

import massprops
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "export")

A3 = (420.0, 297.0)
SCALE = 1 / 6.0
LW_OUT, LW_THIN, LW_DIM, LW_CL = 0.9, 0.45, 0.35, 0.3
FSS = 6.0
CL_DASH = (0, (8, 2, 1.5, 2))

for family in ("Microsoft YaHei", "SimHei", "DejaVu Sans"):
    if family in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams["font.family"] = family
        break
plt.rcParams["axes.unicode_minus"] = False


def sheet(title):
    fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A3[0])
    ax.set_ylim(0, A3[1])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((10, 10), A3[0] - 20, A3[1] - 20, fill=False, lw=LW_OUT, ec="k"))
    ax.add_patch(Rectangle((A3[0] - 158, 12), 146, 26, fill=False, lw=LW_OUT, ec="k"))
    ax.text(A3[0] - 154, 31, "STEM-E 底盘  4WS mobile base", fontsize=8.5)
    ax.text(A3[0] - 154, 24, title, fontsize=7)
    ax.text(A3[0] - 154, 17, "单位 mm   比例 1:6   由 mech/chassis/drawing.py 生成", fontsize=5.5)
    return fig, ax


def dim_h(ax, x0, x1, y, text, fs=FSS):
    for x in (x0, x1):
        ax.plot([x, x], [y - 2, y + 2], lw=LW_DIM, color="k")
    ax.annotate("", (x0, y), (x1, y), arrowprops=dict(arrowstyle="<->", lw=LW_DIM, color="k"))
    ax.text((x0 + x1) / 2, y + 1.0, text, ha="center", va="bottom", fontsize=fs)


def dim_v(ax, y0, y1, x, text, fs=FSS):
    for y in (y0, y1):
        ax.plot([x - 2, x + 2], [y, y], lw=LW_DIM, color="k")
    ax.annotate("", (x, y0), (x, y1), arrowprops=dict(arrowstyle="<->", lw=LW_DIM, color="k"))
    ax.text(x + 1.2, (y0 + y1) / 2, text, ha="left", va="center", fontsize=fs, rotation=90)


def leader(ax, px, py, tx, ty, text, ha="left", fs=FSS):
    ax.plot([px, tx], [py, ty], lw=LW_DIM, color="k")
    tail = 3 if ha == "left" else -3
    ax.plot([tx, tx + tail], [ty, ty], lw=LW_DIM, color="k")
    ax.text(tx + (4 if ha == "left" else -4), ty, text, ha=ha, va="center", fontsize=fs)


def centre_lines(ax, cx, cy, r):
    ax.plot([cx - r, cx + r], [cy, cy], lw=LW_CL, color="k", ls=CL_DASH)
    ax.plot([cx, cx], [cy - r, cy + r], lw=LW_CL, color="k", ls=CL_DASH)


# ------------------------------------------------------------------- sheet 1

def plan(ax, ox, oy):
    s = SCALE
    L, W = P.BODY_L * s, P.BODY_W * s
    ax.add_patch(Rectangle((ox - L / 2, oy - W / 2), L, W, fill=False, lw=LW_OUT, ec="k"))
    for _, x, y in P.CORNERS:
        cx, cy = ox + x * s, oy + y * s
        r = P.SWEEP_CLEAR_R * s
        ax.add_patch(Circle((cx, cy), r, fill=False, lw=LW_THIN, ec="k", ls=(0, (5, 3))))
        ax.add_patch(Rectangle((cx - P.HUB_TIRE_OD / 2 * s, cy - P.HUB_TREAD_W / 2 * s),
                               P.HUB_TIRE_OD * s, P.HUB_TREAD_W * s,
                               fill=False, lw=LW_OUT, ec="k"))
        centre_lines(ax, cx, cy, r + 3)
    bp = (P.BASE_PLATE_L * s, P.BASE_PLATE_W * s)
    ax.add_patch(Rectangle((ox - bp[0] / 2, oy - bp[1] / 2), bp[0], bp[1],
                           fill=False, lw=LW_THIN, ec="k", ls=(0, (4, 2))))
    bt = (P.BATTERY_L * s, P.BATTERY_W * s)
    bx = ox + P.BATTERY_X * s
    ax.add_patch(Rectangle((bx - bt[0] / 2, oy - bt[1] / 2), bt[0], bt[1],
                           fill=False, lw=LW_THIN, ec="k"))
    ax.text(bx, oy, "电池 24V 30Ah", ha="center", va="center", fontsize=FSS)
    for sx in (-1.0, 1.0):
        cx = ox + sx * P.CROSS_X * s
        ax.plot([cx, cx], [oy - P.SPINE_Y * s, oy + P.SPINE_Y * s],
                lw=LW_THIN, color="k", ls=(0, (4, 2)))
    ax.add_patch(Circle((ox, oy), P.COLUMN_PCD / 2 * s, fill=False, lw=LW_CL, ec="k",
                        ls=(0, (6, 2, 1, 2))))
    ax.add_patch(Circle((ox, oy), P.COLUMN_SPIGOT_OD / 2 * s, fill=False, lw=LW_OUT, ec="k"))
    for i in range(P.COLUMN_BOLTS):
        a = math.radians(360.0 * i / P.COLUMN_BOLTS)
        ax.add_patch(Circle((ox + P.COLUMN_PCD / 2 * s * math.cos(a),
                             oy + P.COLUMN_PCD / 2 * s * math.sin(a)),
                            4.5 * s, fill=False, lw=LW_OUT, ec="k"))
    leader(ax, ox + P.COLUMN_PCD / 2 * s * 0.707, oy - P.COLUMN_PCD / 2 * s * 0.707,
           ox + L / 2 - 2, oy - W / 2 + 6,
           "升降柱接口 %dxM8 PCD Ø%.0f + Ø%.0f 止口" % (P.COLUMN_BOLTS, P.COLUMN_PCD,
                                                 P.COLUMN_SPIGOT_OD),
           ha="right")
    ax.text(ox, oy - P.SPINE_Y * s - 6, "虚线为底板与横梁", ha="center", va="top", fontsize=FSS)

    dim_h(ax, ox - P.WHEELBASE / 2 * s, ox + P.WHEELBASE / 2 * s, oy - W / 2 - 9,
          "轴距 %.0f" % P.WHEELBASE)
    dim_h(ax, ox - L / 2, ox + L / 2, oy - W / 2 - 19, "车体全长 %.0f" % P.BODY_L)
    dim_v(ax, oy - P.TRACK / 2 * s, oy + P.TRACK / 2 * s, ox + L / 2 + 8,
          "轮距 %.0f" % P.TRACK)
    dim_v(ax, oy - W / 2, oy + W / 2, ox + L / 2 + 18, "车体全宽 %.0f" % P.BODY_W)
    k = P.SWEEP_CLEAR_R * s * 0.707
    leader(ax, ox - P.WHEELBASE / 2 * s - k, oy + P.TRACK / 2 * s + k,
           ox - L / 2 + 2, oy + W / 2 + 6,
           "转向扫掠 Ø%.0f   软件限位 ±%.0f°" % (2 * P.SWEEP_CLEAR_R, P.STEER_LIMIT_DEG))
    ax.annotate("", (ox + L / 2, oy + W / 2 + 6), (ox + L / 2 - 18, oy + W / 2 + 6),
                arrowprops=dict(arrowstyle="-|>", lw=0.8, color="k"))
    ax.text(ox + L / 2 - 20, oy + W / 2 + 6, "前进 +X", ha="right", va="center", fontsize=FSS)
    ax.text(ox - L / 2, oy + W / 2 + 14, "俯视图", fontsize=8)


def _body_with_arches(ax, ox, oy, half_span, centres, s):
    """Elevation outline of the shell, with a wheel opening at each corner."""
    z0, z1 = P.GROUND_CLEARANCE * s, P.DECK_Z * s
    za = P.SWEEP_CLEAR_Z * s
    r = P.SWEEP_CLEAR_R * s
    ax.plot([ox - half_span, ox + half_span], [oy + z1, oy + z1], lw=LW_OUT, color="k")
    for sgn in (-1, 1):
        ax.plot([ox + sgn * half_span] * 2, [oy + za, oy + z1], lw=LW_OUT, color="k")
    edges = sorted([ox + c * s + sgn * r for c in centres for sgn in (-1, 1)])
    for a, b in ((edges[1], edges[2]),):
        ax.plot([a, b], [oy + z0, oy + z0], lw=LW_OUT, color="k")
    for c in centres:
        inner = ox + c * s + (r if c < 0 else -r)
        ax.plot([inner, inner], [oy + z0, oy + za], lw=LW_OUT, color="k")
        outer = ox + c * s + (-r if c < 0 else r)
        ax.plot([min(inner, outer) if False else outer,
                 ox + (half_span if c > 0 else -half_span)],
                [oy + za, oy + za], lw=LW_OUT, color="k")
        ax.plot([ox + c * s - r, ox + c * s + r], [oy + za, oy + za], lw=LW_OUT, color="k")


def side(ax, ox, oy):
    """Elevation looking along +Y.  ``oy`` is the ground line."""
    s = SCALE
    L = P.BODY_L * s
    ax.plot([ox - L / 2 - 14, ox + L / 2 + 14], [oy, oy], lw=LW_OUT, color="k")
    _body_with_arches(ax, ox, oy, L / 2, (-P.WHEELBASE / 2, P.WHEELBASE / 2), s)
    for x in (-P.WHEELBASE / 2, P.WHEELBASE / 2):
        cx = ox + x * s
        cz = oy + P.WHEEL_AXIS_Z * s
        ax.add_patch(Circle((cx, cz), P.HUB_TIRE_OD / 2 * s, fill=False, lw=LW_OUT, ec="k"))
        ax.add_patch(Circle((cx, cz), P.HUB_RIM_OD / 2 * s, fill=False, lw=LW_THIN, ec="k"))
        centre_lines(ax, cx, cz, P.HUB_TIRE_OD / 2 * s + 3)
    for z, lab in ((P.BASE_PLATE_Z0, "底板 %.0f" % P.BASE_PLATE_Z0),
                   (P.TOP_PLATE_Z0, "甲板 %.0f" % P.TOP_PLATE_Z0)):
        ax.plot([ox - L * 0.22, ox + L * 0.22], [oy + z * s, oy + z * s],
                lw=LW_THIN, color="k", ls=(0, (4, 2)))
        ax.text(ox, oy + z * s + 1, lab, fontsize=FSS, ha="center", va="bottom")
    dim_v(ax, oy, oy + P.GROUND_CLEARANCE * s, ox - L / 2 - 7,
          "离地 %.0f" % P.GROUND_CLEARANCE)
    dim_v(ax, oy, oy + P.HUB_TIRE_OD * s, ox - L / 2 - 17, "Ø%.0f" % P.HUB_TIRE_OD)
    dim_v(ax, oy, oy + P.DECK_Z * s, ox + L / 2 + 7, "全高 %.0f" % P.DECK_Z)
    ax.text(ox - L / 2, oy + P.DECK_Z * s + 5, "侧视图", fontsize=8)


def front(ax, ox, oy):
    s = SCALE
    W = P.BODY_W * s
    ax.plot([ox - W / 2 - 14, ox + W / 2 + 14], [oy, oy], lw=LW_OUT, color="k")
    _body_with_arches(ax, ox, oy, W / 2, (-P.TRACK / 2, P.TRACK / 2), s)
    for y in (-P.TRACK / 2, P.TRACK / 2):
        cy = ox + y * s
        sgn = 1.0 if y > 0 else -1.0
        tw = P.HUB_TREAD_W * s
        ax.add_patch(Rectangle((cy - tw / 2, oy), tw, P.HUB_TIRE_OD * s,
                               fill=False, lw=LW_OUT, ec="k"))
        # everything inboard of the shell is a hidden line in an external view
        hid = dict(fill=False, lw=LW_THIN, ec="0.35", ls=(0, (3, 2)))
        fy = cy - sgn * P.HUB_FLANGE_OFFSET * s
        yk = cy - sgn * (P.HUB_FLANGE_OFFSET + P.YOKE_PLATE_T) * s
        ax.add_patch(Rectangle((min(fy, yk), oy + 37.5 * s), abs(fy - yk),
                               (P.YOKE_TOP_Z1 - 37.5) * s, **hid))
        edge = cy + sgn * 35 * s
        ax.add_patch(Rectangle((min(yk, edge), oy + P.YOKE_TOP_Z0 * s), abs(edge - yk),
                               P.YOKE_TOP_T * s, **hid))
        for w, z0, z1 in (
            (P.KINGPIN_OD, P.KINGPIN_Z0, P.KINGPIN_Z1),
            (P.HOUSING_W, P.HOUSING_Z0, P.HOUSING_Z1),
            (P.STEER_OD, P.STEER_OUT_Z, P.STEER_REAR_Z),
        ):
            ax.add_patch(Rectangle((cy - w / 2 * s, oy + z0 * s), w * s, (z1 - z0) * s, **hid))
        ax.plot([cy, cy], [oy - 4, oy + (P.MODULE_TOP_Z + 8) * s], lw=LW_CL, color="k",
                ls=CL_DASH)
    dim_h(ax, ox - P.TRACK / 2 * s, ox + P.TRACK / 2 * s, oy - 8, "轮距 %.0f" % P.TRACK)
    dim_h(ax, ox - W / 2, ox + W / 2, oy - 17, "车体全宽 %.0f" % P.BODY_W)
    ax.text(ox + W / 2 + 4, oy + P.HOUSING_Z0 * s, "虚线为内部件", fontsize=FSS, va="center")
    ax.text(ox - W / 2, oy + P.DECK_Z * s + 5, "正视图（由前方看）", fontsize=8)


def data_block(ax, x, y):
    curb, curb_z, _, _ = massprops.chassis_mass_properties()
    total = curb + P.UPPER_BODY_MASS + P.PAYLOAD_MASS
    rows = [
        ("驱动架构", "四轮四转 4WS，零主销偏距"),
        ("轮毂电机", "DM-H65 x4，24V，6.0/21.5 Nm，Ø171 实心胎"),
        ("转向电机", "DM-J4340-2EC x4，40:1，9/27 Nm，直驱主销"),
        ("驱动器", "DM6540-1EC x4，分体式，车内安装"),
        ("轴距 x 轮距", "%.0f x %.0f" % (P.WHEELBASE, P.TRACK)),
        ("车体 长宽高", "%.0f x %.0f x %.0f" % (P.BODY_L, P.BODY_W, P.DECK_Z)),
        ("离地间隙", "%.0f" % P.GROUND_CLEARANCE),
        ("升降柱接口", "%d x M8 @ PCD Ø%.0f + Ø%.0f 止口，局部 %.0f mm"
         % (P.COLUMN_BOLTS, P.COLUMN_PCD, P.COLUMN_SPIGOT_OD,
            P.TOP_PLATE_T + P.COLUMN_DOUBLER_T)),
        ("底盘整备质量", "%.1f kg，质心高 %.0f mm" % (curb, curb_z)),
        ("设计总质量", "%.1f kg（上半身 %.0f + 负载 %.0f）"
         % (total, P.UPPER_BODY_MASS, P.PAYLOAD_MASS)),
        ("额定车速", "%.2f m/s（120 rpm）" % P.V_RATED),
        ("四轮牵引力", "额定 %.0f N，峰值 %.0f N" % (P.F_TRACTIVE_RATED, P.F_TRACTIVE_PEAK)),
        ("母线电流 24V", "额定 %.1f A，峰值 %.1f A" % (P.I_BUS_RATED, P.I_BUS_PEAK)),
        ("悬挂", "滑柱式独立，常规 ±%.0f，机械 ±%.0f，%.0f N/mm"
         % (P.SUSP_TRAVEL_NOMINAL, P.SUSP_TRAVEL_MECH, P.SUSP_RATE)),
        ("称重", "每角 2 个 %.0f kg，跨主销对称，8 个" % P.LOADCELL_RANGE_KG),
        ("驻车", "无机械刹车，四轮 X 型互锁"),
        ("电池位置", "后舱 x=%.0f，由车体后部抽出；前舱留给电控" % P.BATTERY_X),
        ("过门", "4WS 横移通过，净宽 ≥750 时单边余量 %.0f" % ((750 - P.BODY_W) / 2)),
        ("侧向作业", "硬件按 %.0f 定尺寸；实际范围由动态包络实时给出"
         % P.ARM_REACH_LAT),
        ("急停", "%.1f m/s2，Cat-1 受控停机，禁止短接相线" % P.ESTOP_DECEL),
    ]
    h = 6.6 * len(rows) + 8
    ax.add_patch(Rectangle((x, y), 176, h, fill=False, lw=LW_OUT, ec="k"))
    ax.text(x + 3, y + h - 5, "技术数据", fontsize=8)
    for i, (k, v) in enumerate(rows):
        yy = y + 6.6 * (len(rows) - 1 - i) + 2.6
        ax.text(x + 3, yy, k, fontsize=FSS)
        ax.text(x + 44, yy, v, fontsize=FSS)
        if i:
            ax.plot([x, x + 176], [yy + 4.6, yy + 4.6], lw=0.2, color="0.65")


def sheet1():
    fig, ax = sheet("图 1/2  总布置  general arrangement")
    plan(ax, 103, 205)
    side(ax, 103, 60)
    front(ax, 272, 60)
    data_block(ax, 222, 152)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(os.path.join(OUT, "GA_sheet1." + ext), dpi=200)
    plt.close(fig)


# ------------------------------------------------------------------- sheet 2

def corner_section(ax, ox, oy, s=0.42):
    """Section through one corner module, looking along +X at the left front."""
    def R(y0, y1, z0, z1, lw=LW_THIN, **kw):
        ax.add_patch(Rectangle((ox + y0 * s, oy + z0 * s), (y1 - y0) * s, (z1 - z0) * s,
                               fill=False, lw=lw, ec="k", **kw))

    ax.plot([ox - 136 * s, ox + 72 * s], [oy, oy], lw=LW_OUT, color="k")
    ax.plot([ox, ox], [oy - 5, oy + (P.MODULE_TOP_Z + 50) * s], lw=LW_CL, color="k", ls=CL_DASH)

    R(-P.HUB_TREAD_W / 2, P.HUB_TREAD_W / 2, 0, P.HUB_TIRE_OD, lw=LW_OUT)
    R(-(P.HUB_FLANGE_OFFSET - 2), P.HUB_OVERALL_W - P.HUB_FLANGE_OFFSET,
      (P.HUB_TIRE_OD - P.HUB_RIM_OD) / 2, (P.HUB_TIRE_OD + P.HUB_RIM_OD) / 2)
    fy = -P.HUB_FLANGE_OFFSET
    R(fy, fy + 2, P.WHEEL_AXIS_Z - P.HUB_FLANGE_BOSS_OD / 2,
      P.WHEEL_AXIS_Z + P.HUB_FLANGE_BOSS_OD / 2, lw=LW_OUT)
    R(fy - P.YOKE_PLATE_T, fy, 37.5, P.YOKE_TOP_Z1, lw=LW_OUT)
    R(fy - P.YOKE_PLATE_T, 35, P.YOKE_TOP_Z0, P.YOKE_TOP_Z1, lw=LW_OUT)
    R(-P.KINGPIN_OD / 2, P.KINGPIN_OD / 2, P.KINGPIN_Z0, P.KINGPIN_Z1, lw=LW_OUT)
    R(-P.KINGPIN_ID / 2, P.KINGPIN_ID / 2, P.KINGPIN_Z0, P.KINGPIN_Z1)
    R(-P.TUBE_FLANGE_OD / 2, P.TUBE_FLANGE_OD / 2, P.KINGPIN_Z0, P.KINGPIN_Z0 + 6)
    R(-P.TUBE_FLANGE_OD / 2, P.TUBE_FLANGE_OD / 2, P.TUBE_FLANGE_Z0,
      P.TUBE_FLANGE_Z0 + P.TUBE_FLANGE_T)
    for z in (P.BEARING_LO_Z, P.BEARING_HI_Z):
        for sgn in (-1, 1):
            lo, hi = sorted((sgn * P.KINGPIN_OD / 2, sgn * P.BEARING_OD / 2))
            R(lo, hi, z, z + P.BEARING_W, lw=LW_OUT)
    R(-P.HOUSING_W / 2, P.HOUSING_W / 2, P.HOUSING_Z0, P.HOUSING_Z1, lw=LW_OUT)
    R(-P.DIAPHRAGM_OD / 2, P.DIAPHRAGM_OD / 2, P.DIAPHRAGM_Z0,
      P.DIAPHRAGM_Z0 + P.DIAPHRAGM_T, lw=LW_OUT)
    R(-P.STEER_OD / 2, P.STEER_OD / 2, P.STEER_OUT_Z, P.STEER_REAR_Z, lw=LW_OUT)
    R(-P.HOUSING_L / 2, P.HOUSING_L / 2, P.STEER_REAR_Z, P.MODULE_TOP_Z, lw=LW_OUT)
    R(P.RAIL_Y - 6, P.RAIL_Y + 6, P.RAIL_Z0, P.RAIL_Z0 + P.RAIL_LEN, lw=LW_OUT)
    R(-P.LOADCELL_OD / 2, P.LOADCELL_OD / 2, P.HOUSING_Z1, P.HOUSING_Z1 + P.LOADCELL_H,
      ls=(0, (3, 2)))
    R(-P.SPRING_OD / 2, P.SPRING_OD / 2, P.HOUSING_Z1 + P.LOADCELL_H, P.TOP_PLATE_Z0,
      ls=(0, (3, 2)))
    R(-136, 72, P.TOP_PLATE_Z0, P.DECK_Z, lw=LW_OUT)

    # Notes are ordered by the height of the feature they point at, and split
    # left and right by which side of the kingpin that feature sits on, so no
    # two leaders cross each other or the section.
    right = [
        (P.HOUSING_L / 2, P.MODULE_TOP_Z, 192, "转向电机支架"),
        (P.STEER_OD / 2, (P.STEER_OUT_Z + P.STEER_REAR_Z) / 2, 178, "DM-J4340-2EC，只传扭矩"),
        (P.DIAPHRAGM_OD / 2, P.DIAPHRAGM_Z0 + P.DIAPHRAGM_T, 166,
         "膜片联轴盘 t%.0f，消除过定位" % P.DIAPHRAGM_T),
        (P.BEARING_OD / 2, P.BEARING_HI_Z, 154,
         "6810 x2，间距 %.0f，承担全部力与力矩" % (P.BEARING_HI_Z - P.BEARING_LO_Z)),
        (P.KINGPIN_ID / 2, (P.BEARING_LO_Z + P.BEARING_HI_Z) / 2, 142,
         "中空主销 Ø%.0f / Ø%.0f，电机线走轴心" % (P.KINGPIN_OD, P.KINGPIN_ID)),
    ]
    left = [
        (-P.SPRING_OD / 2, P.TOP_PLATE_Z0 - 20, 192,
         "模具弹簧 x2 @ x=±%.0f，%.0f N/mm" % (P.SUSP_SPRING_X, P.SUSP_RATE)),
        (P.RAIL_Y - 6, P.RAIL_Z0 + P.RAIL_LEN - 10, 176, "MGN12 滚珠导轨 x2"),
        (-P.LOADCELL_OD / 2, P.HOUSING_Z1 + P.LOADCELL_H / 2, 160,
         "称重传感器 x2，%.0f kg" % P.LOADCELL_RANGE_KG),
        (fy, P.WHEEL_AXIS_Z, 86, "DM-H65 法兰接口，见右图"),
    ]
    for py, pz, ty, text in right:
        leader(ax, ox + py * s, oy + pz * s, ox + 76 * s, ty, text)
    for py, pz, ty, text in left:
        leader(ax, ox + py * s, oy + pz * s, ox - 100 * s, ty, text, ha="right")

    dim_v(ax, oy, oy + P.HUB_TIRE_OD * s, ox - 66 * s, "Ø%.0f" % P.HUB_TIRE_OD)
    dim_v(ax, oy + P.BEARING_LO_Z * s, oy + P.BEARING_HI_Z * s, ox + 46 * s,
          "%.0f" % (P.BEARING_HI_Z - P.BEARING_LO_Z))
    dim_v(ax, oy, oy + P.DECK_Z * s, ox + 78 * s, "全高 %.0f" % P.DECK_Z)
    dim_h(ax, ox + fy * s, ox, oy - 9, "悬臂偏距 %.2f" % P.HUB_FLANGE_OFFSET)
    ax.text(ox - 100 * s, oy + (P.MODULE_TOP_Z + 56) * s,
            "四角模块剖面（沿 +X 看，左前角）", fontsize=8)


def hub_interface(ax, ox, oy, s=1.6):
    ax.add_patch(Circle((ox, oy), P.HUB_FLANGE_BOSS_OD / 2 * s, fill=False, lw=LW_OUT, ec="k"))
    ax.add_patch(Circle((ox, oy), P.HUB_FLANGE_PCD / 2 * s, fill=False, lw=LW_CL, ec="k",
                        ls=(0, (6, 2, 1, 2))))
    ax.add_patch(Circle((ox, oy), 10 * s, fill=False, lw=LW_THIN, ec="k"))
    r = P.HUB_FLANGE_PCD / 2 * s
    for a in P.HUB_FLANGE_M5_ANGLES:
        ax.add_patch(Circle((ox + r * math.cos(math.radians(a)), oy + r * math.sin(math.radians(a))),
                            2.75 * s, fill=False, lw=LW_OUT, ec="k"))
    for a in P.HUB_FLANGE_DOWEL_ANGLES:
        ax.add_patch(Circle((ox + r * math.cos(math.radians(a)), oy + r * math.sin(math.radians(a))),
                            P.HUB_FLANGE_DOWEL_D / 2 * s, fill=False, lw=LW_OUT, ec="k",
                            ls=(0, (2, 1))))
    centre_lines(ax, ox, oy, P.HUB_FLANGE_BOSS_OD / 2 * s + 7)
    leader(ax, ox + r * 0.707, oy + r * 0.707, ox + 32, oy + 30,
           "6 x M5 深10 max  @ ±45° ±90° ±135°")
    leader(ax, ox + r, oy, ox + 32, oy + 20, "2 x Ø4 H7 定位销 @ 0° 180°")
    leader(ax, ox + r * 0.707, oy - r * 0.707, ox + 32, oy - 22, "螺栓孔节圆 PCD Ø25.00")
    leader(ax, ox - P.HUB_FLANGE_BOSS_OD / 2 * s, oy, ox - 32, oy - 30, "凸台 Ø35.2", ha="right")
    leader(ax, ox - 7 * s, oy + 7 * s, ox - 32, oy + 28, "中心出线孔 Ø20", ha="right")
    ax.text(ox - 46, oy + 46, "DM-H65 安装接口  放大 1.6:1  官方 STEP 实测", fontsize=8)


def sheet2():
    fig, ax = sheet("图 2/2  四角模块与安装接口  corner module")
    corner_section(ax, 108, 45)
    hub_interface(ax, 310, 212)
    ax.text(214, 152, "装配与限位说明", fontsize=8)
    notes = [
        "1  主销轴线通过轮胎接地点，零偏距。原地转向阻力矩约 1.8 Nm，满载单轮约 3.2 Nm，",
        "     对 DM-J4340-2EC 额定 9 Nm 有 3 至 5 倍余量，不需要额外减速级。",
        "2  轮毂电机线从法兰中心引出，经转向叉进入中空主销，在上轴承下方侧窗引出车内。",
        "     转向软件限位 ±%.0f°，机械硬限位由转向叉与导轨支座碰撞提供。" % P.STEER_LIMIT_DEG,
        "3  两个 6810 轴承间距 %.0f mm，承受 %.2f mm 悬臂产生的倾覆力矩，单轴承径向力约 %.0f N，"
        % (P.BEARING_HI_Z - P.BEARING_LO_Z, P.HUB_FLANGE_OFFSET,
           8.5 / ((P.BEARING_HI_Z - P.BEARING_LO_Z) / 1000.0)),
        "     相对其额定动载荷有数十倍余量。DM-J4340-2EC 不参与承力。",
        "4  膜片联轴盘消除主销双轴承与转向电机自身轴承之间的过定位，装配时不需要研配。",
        "5  悬挂常规行程 ±%.0f mm 补偿地坪不平；机械行程 ±%.0f mm 为冲击储备，由聚氨酯"
        % (P.SUSP_TRAVEL_NOMINAL, P.SUSP_TRAVEL_MECH),
        "     渐进缓冲块吸收。刚度 %.0f N/mm，满载前伸造成的手端漂移约 5 mm。" % P.SUSP_RATE,
        "6  每角两个传感器跨主销对称布置，使弹簧力不对导轨产生力矩。偏置布置的静摩擦带为",
        "     5.9 N，对称布置降到 2.1 N，称重误差从 1.21 kg 降到 0.43 kg，见 error_budget.py。",
        "7  四角读数的加权平均直接给出重心水平投影，并可反算俯仰角供机械臂补偿。",
        "8  无机械驻车制动。停车时四轮转成 X 型互锁；断电后整车可被推动，属已知残留风险。",
    ]
    for i, t in enumerate(notes):
        ax.text(214, 144 - i * 6.2, t, fontsize=FSS)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(os.path.join(OUT, "GA_sheet2." + ext), dpi=200)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    sheet1()
    sheet2()
    print("wrote GA_sheet1/2 .pdf .svg .png to", OUT)
