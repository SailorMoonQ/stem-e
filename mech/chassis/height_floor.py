"""What actually sets the deck height, and what each way of lowering it costs.

    python height_floor.py

The deck underside has to clear two things at once: the top of the corner
module plus its suspension travel, and the top of the spring that the deck
itself seats.  Whichever is taller wins, and only that one is worth attacking.
"""

import params as P

LOADCELL_BUTTON_H = 15.0     # compression button cell instead of a 30 mm column
SPRING_LIGHT = 42.0          # light duty die spring, 40 percent max deflection
SPRING_MEDIUM = 58.0         # what the model carries today
BELT_MODULE_TOP = P.KINGPIN_Z1 + 22.0   # pulley on the tube instead of the motor


def deck_underside(module_top, housing_top, loadcell_h, spring_free, travel):
    by_module = module_top + travel
    by_spring = housing_top + loadcell_h + spring_free
    return max(by_module, by_spring), by_module, by_spring


def show(label, **kw):
    u, m, s = deck_underside(**kw)
    binds = "模块顶" if m >= s else "弹簧"
    print("  %-40s 甲板 %5.1f   模块 %5.1f  弹簧 %5.1f   卡在%s"
          % (label, u + P.TOP_PLATE_T, m, s, binds))


def main():
    print("当前设计")
    show("现状", module_top=P.MODULE_TOP_Z, housing_top=P.HOUSING_Z1,
         loadcell_h=P.LOADCELL_H, spring_free=SPRING_MEDIUM,
         travel=P.SUSP_TRAVEL_MECH)

    print("\n只换零件，不改架构")
    show("换 15 mm 按钮式传感器", module_top=P.MODULE_TOP_Z, housing_top=P.HOUSING_Z1,
         loadcell_h=LOADCELL_BUTTON_H, spring_free=SPRING_MEDIUM,
         travel=P.SUSP_TRAVEL_MECH)
    show("再换 42 mm 轻载模具弹簧", module_top=P.MODULE_TOP_Z, housing_top=P.HOUSING_Z1,
         loadcell_h=LOADCELL_BUTTON_H, spring_free=SPRING_LIGHT,
         travel=P.SUSP_TRAVEL_MECH)
    show("再把机械行程压到 ±8", module_top=P.MODULE_TOP_Z, housing_top=P.HOUSING_Z1,
         loadcell_h=LOADCELL_BUTTON_H, spring_free=SPRING_LIGHT, travel=8.0)

    print("\n把转向电机从主销正上方挪走（同步带旁置）")
    show("只旁置", module_top=BELT_MODULE_TOP, housing_top=P.HOUSING_Z1,
         loadcell_h=P.LOADCELL_H, spring_free=SPRING_MEDIUM,
         travel=P.SUSP_TRAVEL_MECH)
    show("旁置 + 按钮传感器 + 轻载弹簧", module_top=BELT_MODULE_TOP,
         housing_top=P.HOUSING_Z1, loadcell_h=LOADCELL_BUTTON_H,
         spring_free=SPRING_LIGHT, travel=P.SUSP_TRAVEL_MECH)
    show("再把轴承座顶面降到 240", module_top=BELT_MODULE_TOP, housing_top=240.0,
         loadcell_h=LOADCELL_BUTTON_H, spring_free=SPRING_LIGHT,
         travel=P.SUSP_TRAVEL_MECH)

    print("\n降高换来什么")
    for drop in (6.0, 34.0, 64.0):
        frame_saved = 19.0 * drop / (P.DECK_Z - P.BASE_PLATE_Z0)
        cog_drop = drop * 0.5 * frame_saved / 61.0
        print("  降 %4.1f mm -> 车架省约 %.1f kg，底盘质心降约 %.1f mm，"
              "升降柱行程多 %.0f mm" % (drop, frame_saved, cog_drop, drop))


if __name__ == "__main__":
    main()
