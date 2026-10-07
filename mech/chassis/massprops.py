"""Mass and centre of gravity taken from the solid model, not from estimates.

Machined parts get their volume and centroid straight out of the kernel.
Bought-in items that are modelled as envelopes (hub motors, actuators, battery)
carry their catalogue mass at the centroid of that envelope.  Items too small
to model (bearings, fasteners, rail carriages, wiring) are lumped at a stated
location so the number is auditable rather than hidden in a fudge factor.
"""

import cadquery as cq

import model
import params as P

# name -> (count, density kg/mm^3) for parts whose mass comes from geometry
MACHINED = {
    "steering_yoke": (4, P.ALU_DENSITY),
    "kingpin_tube": (4, P.ALU_DENSITY),
    "bearing_housing": (4, P.ALU_DENSITY),
    "steer_bracket": (4, P.ALU_DENSITY),
    "frame": (1, P.ALU_DENSITY),
    "shell_skirt": (1, P.SHELL_DENSITY),
    "shell_upper": (1, P.SHELL_DENSITY),
    "shell_belt": (1, P.SHELL_DENSITY),
    "shell_cover": (1, P.SHELL_DENSITY),
    "shell_panels": (1, P.SHELL_DENSITY),
    "estop": (1, P.ALU_DENSITY),
}

# name -> (count, mass kg each) for bought-in items modelled as envelopes
BOUGHT_MODELLED = {
    "hub_motor": (4, P.HUB_MASS),
    "steer_motor": (4, P.STEER_MASS),
    "battery": (1, P.BATTERY_MASS),
    "drivers": (1, 4 * 0.09),
    "electronics": (1, P.ELEC_MASS),
}

# name -> (mass kg, z mm) for items not modelled, placed by hand
LUMPED = {
    "bearings_fasteners": (2.0, 230.0),
    "rail_carriages": (4 * 0.35, 230.0),
    "springs_loadcells": (4 * 0.45, 290.0),
    "wiring_connectors": (1.6, 150.0),
}


def _centroid(shape):
    c = shape.val().Center()
    return c.x, c.z


def chassis_mass_properties():
    """Return (total kg, cog_z mm, rows) for the chassis without the upper body.

    Rows are (name, count, mass kg, cog x mm, cog z mm).  The fore and aft
    position matters as much as the height: moving the battery into the rear
    bay buys forward tipping margin directly, and that only shows up if the
    x coordinate is carried through.
    """
    rows = []
    for name, (count, rho) in MACHINED.items():
        s = getattr(model, name)()
        x, z = _centroid(s)
        rows.append((name, count, s.val().Volume() * rho * count, x, z))
    for name, (count, each) in BOUGHT_MODELLED.items():
        s = getattr(model, name)()
        x, z = _centroid(s)
        rows.append((name, count, each * count, x, z))
    for name, (m, z) in LUMPED.items():
        rows.append((name, 1, m, 0.0, z))

    total = sum(r[2] for r in rows)
    cog_z = sum(r[2] * r[4] for r in rows) / total
    cog_x = sum(r[2] * r[3] for r in rows) / total
    return total, cog_z, rows, cog_x


if __name__ == "__main__":
    total, cog_z, rows, cog_x = chassis_mass_properties()
    print("%-22s %5s %8s %9s %9s" % ("item", "qty", "kg", "cog x mm", "cog z mm"))
    for name, count, m, x, z in sorted(rows, key=lambda r: -r[2]):
        print("%-22s %5d %8.2f %9.1f %9.1f" % (name, count, m, x, z))
    print("%-22s %5s %8.2f %9.1f %9.1f" % ("CHASSIS TOTAL", "", total, cog_x, cog_z))
