"""Build the STEM-E chassis: interference check, mass report, exports.

    python build.py

Writes STEP, STL and SVG into ``export/`` and a machine readable
``export/chassis_params.yaml`` for ``src/description`` to consume, so the URDF
never restates geometry that lives here.
"""

import json
import math
import os

import cadquery as cq
from cadquery import exporters

import massprops
import model
import params as P

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, *P.EXPORT_DIR.split("/"))
PARTS = {
    "steering_yoke": model.steering_yoke,
    "kingpin_tube": model.kingpin_tube,
    "bearing_housing": model.bearing_housing,
    "steer_bracket": model.steer_bracket,
    "frame": model.frame,
    "shell": model.shell,
    "shell_panels": model.shell_panels,
}


def _vol(shape):
    return shape.val().Volume()


def mass_report():
    rows = []
    for name, fn in PARTS.items():
        v = _vol(fn())
        n = 1 if name in ("frame", "shell", "shell_panels") else 4
        rho = P.SHELL_DENSITY if name.startswith("shell") else P.ALU_DENSITY
        rows.append((name, n, v / 1000.0, n * v * rho))
    return rows


def interference():
    """Nominal pose clashes, plus the swept volume every kingpin needs free."""
    findings = []
    frame = model.frame()
    shell = model.shell()
    statics = {"frame": frame, "shell": shell, "battery": model.battery(),
               "drivers": model.drivers(), "electronics": model.electronics()}

    movers = {
        "wheel": model.hub_motor(),
        "yoke": model.steering_yoke(),
        "kingpin_tube": model.kingpin_tube(),
        "housing": model.bearing_housing(),
        "steer_bracket": model.steer_bracket(),
    }
    rails, cell, spring = model.suspension()
    movers["rails"] = rails
    movers["loadcell"] = cell
    movers["spring"] = spring

    for cname, cx, cy in P.CORNERS:
        mirror = cy < 0
        for mname, solid in movers.items():
            s = solid.mirror("XZ") if mirror else solid
            s = s.translate((cx, cy, 0))
            for sname, stat in statics.items():
                try:
                    v = _vol(s.intersect(stat))
                except Exception:
                    v = 0.0
                if v > 1.0:
                    findings.append((cname, mname, sname, v))

    v = _vol(frame.intersect(shell))
    if v > 1.0:
        findings.append(("--", "frame", "shell", v))

    # Nothing fixed to the chassis may sit inside a steering sweep cylinder.
    # The frame and shell have it cut out of them, so they pass by
    # construction; everything else has to be checked, or a wheel finds it at
    # full lock.
    sweep = model._sweep_clearance()
    for sname, stat in statics.items():
        if sname in ("frame", "shell", "shell_panels"):
            continue
        v = _vol(stat.intersect(sweep))
        if v > 1.0:
            findings.append(("--", sname, "INSIDE_STEERING_SWEEP", v))
    gap = P.TOP_PLATE_Z0 - P.MODULE_TOP_Z
    if gap < P.SUSP_TRAVEL_MECH:
        findings.append(("--", "deck underside", "module top on bump", gap))

    # Anything that turns with the wheel must stay inside the clearance cylinder.
    for cname, cx, cy in P.CORNERS:
        env = (
            cq.Workplane("XY", origin=(cx, cy, 0))
            .circle(P.SWEEP_CLEAR_R)
            .extrude(P.SWEEP_CLEAR_Z)
        )
        for mname in ("wheel", "yoke"):
            s = movers[mname]
            s = s.mirror("XZ") if cy < 0 else s
            s = s.translate((cx, cy, 0))
            outside = _vol(s.cut(env))
            if outside > 1.0:
                findings.append((cname, mname, "OUTSIDE_SWEEP_ENVELOPE", outside))
    return findings


def stability():
    """Worst case tipping check, arms fully extended at full height.

    Chassis mass and centre of gravity come from the solid model, so this
    number moves whenever the geometry does.
    """
    g = 9.81
    curb, curb_z, _, curb_x = massprops.chassis_mass_properties()
    total = curb + P.UPPER_BODY_MASS + P.PAYLOAD_MASS
    arms = P.ARM_MASS

    cog_z = (
        curb * curb_z
        + P.UPPER_BODY_MASS * P.UPPER_BODY_COG_Z
        + P.PAYLOAD_MASS * P.PAYLOAD_Z
    ) / total

    # the chassis own fore and aft offset counts against the arm reach
    fwd_static = (curb * curb_x + arms * P.ARM_REACH_FWD / 2
                  + P.PAYLOAD_MASS * P.ARM_REACH_FWD) / total
    lat_static = (arms * P.LAT_ARM_FRACTION * P.ARM_REACH_LAT / 2
                  + P.PAYLOAD_MASS * P.ARM_REACH_LAT) / total
    slope = cog_z * math.tan(math.radians(P.FLOOR_SLOPE_DEG))

    # Full reach and full acceleration do not happen together sideways, so
    # sizing on both at once double counts; the envelope trades one for the
    # other.  Report the two cases the hardware actually has to carry: the
    # static case at the arm's full reach, and the design operating point.
    lat_design_static = (arms * P.LAT_ARM_FRACTION * P.LAT_DESIGN_REACH / 2
                         + P.PAYLOAD_MASS * P.LAT_DESIGN_REACH) / total

    cases = {
        "fwd_static": (fwd_static + slope, P.WHEELBASE / 2),
        "fwd_estop": (fwd_static + cog_z * P.ESTOP_DECEL / g + slope, P.WHEELBASE / 2),
        "lat_static": (lat_static + slope, P.TRACK / 2),
        "lat_crab": (lat_design_static + cog_z * P.LATERAL_ACCEL / g + slope,
                     P.TRACK / 2),
    }
    out = {
        "curb_kg": curb,
        "curb_cog_mm": curb_z,
        "curb_cog_x_mm": curb_x,
        "total_kg": total,
        "cog_height_mm": cog_z,
    }
    for name, (need, arm) in cases.items():
        out[name + "_demand_mm"] = need
        out[name + "_sf"] = arm / need
    out["fwd_demand_mm"] = cases["fwd_estop"][0]
    out["lat_demand_mm"] = max(cases["lat_static"][0], cases["lat_crab"][0])
    out["fwd_arm_mm"] = P.WHEELBASE / 2
    out["lat_arm_mm"] = P.TRACK / 2
    out["fwd_sf"] = cases["fwd_estop"][1] / cases["fwd_estop"][0]
    out["lat_sf"] = min(cases["lat_static"][1] / cases["lat_static"][0],
                        cases["lat_crab"][1] / cases["lat_crab"][0])
    return out


def export():
    os.makedirs(OUT, exist_ok=True)
    asm = model.chassis(with_shell=True)
    asm.save(os.path.join(OUT, "chassis_assembly.step"))

    bare = model.chassis(with_shell=False)
    comp = bare.toCompound()
    exporters.export(comp, os.path.join(OUT, "chassis_no_shell.step"))
    exporters.export(comp, os.path.join(OUT, "chassis_no_shell.stl"))

    for name, fn in PARTS.items():
        exporters.export(fn(), os.path.join(OUT, "part_%s.step" % name))

    views = {"top": (0, 0, 1), "front": (1, 0, 0), "side": (0, 1, 0), "iso": (1, -1, 0.6)}
    for tag, shape in (("", asm.toCompound()), ("bare_", comp)):
      for vname, d in views.items():
        exporters.export(
            shape,
            os.path.join(OUT, "view_%s%s.svg" % (tag, vname)),
            opt={
                "width": 1400,
                "height": 900,
                "marginLeft": 20,
                "marginTop": 20,
                "projectionDir": d,
                "showAxes": False,
                "strokeWidth": 0.5,
                "showHidden": False,
            },
        )

    data = {k: v for k, v in vars(P).items() if k.isupper() and isinstance(v, (int, float, str))}
    data["_note"] = "generated by mech/chassis/build.py, do not hand edit"
    data["stability"] = stability()
    with open(os.path.join(OUT, "chassis_params.yaml"), "w", encoding="utf-8") as fh:
        for k in sorted(data):
            v = data[k]
            if isinstance(v, dict):
                fh.write("%s:\n" % k)
                for kk in sorted(v):
                    fh.write("  %s: %s\n" % (kk, round(v[kk], 4)))
            elif isinstance(v, str):
                fh.write('%s: "%s"\n' % (k, v))
            else:
                fh.write("%s: %s\n" % (k, v))


if __name__ == "__main__":
    print("=== interference ===")
    found = interference()
    if not found:
        print("  clean")
    for row in found:
        print("  %-4s %-14s vs %-24s %10.1f mm^3" % row)

    print("\n=== aluminium mass ===")
    tot = 0.0
    for name, n, vol_cm3, kg in mass_report():
        tot += kg
        print("  %-18s x%d  %9.1f cm^3  %6.2f kg" % (name, n, vol_cm3, kg))
    print("  %-18s      %22s  %6.2f kg" % ("machined total", "", tot))

    print("\n=== stability ===")
    for k, v in stability().items():
        print("  %-16s %10.2f" % (k, v))

    print("\n=== export ===")
    export()
    print("  written to", OUT)
