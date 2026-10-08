"""Single source of truth for STEM-E chassis geometry.

All dimensions in millimetres, masses in kilograms, angles in degrees.

Coordinate frame matches ROS ``base_link`` convention:
  +X forward, +Y left, +Z up.
Origin sits at the centre of the four wheel contact patches, on the ground
plane, at nominal ride height.

Vendor numbers in COMPONENTS are measured from the official STEP models and
2D drawings published by Shenzhen DM Technology, not estimated.  Sources:
  https://github.com/dmBots/DM-H65-1EC
  https://github.com/dmBots/DM-J4340-2EC
"""

import math
import os

# --------------------------------------------------------------------------
# Vendor components (measured, do not edit without re-checking the STEP file)
# --------------------------------------------------------------------------

# DM-H65 hub motor, 24V, 6.0 Nm rated / 21.5 Nm peak, 120 rpm rated
HUB_TIRE_OD = 171.0          # crowned tread outside diameter, +/-1
HUB_TIRE_SHOULDER_OD = 163.0
HUB_TREAD_W = 43.8
HUB_OVERALL_W = 66.3         # tread far face to flange mounting face
HUB_RIM_OD = 135.6
HUB_FLANGE_OFFSET = 37.84    # wheel centre plane -> flange mounting face
HUB_FLANGE_BOSS_OD = 35.2
HUB_FLANGE_PCD = 25.0
HUB_FLANGE_M5_ANGLES = (45.0, 90.0, 135.0, 225.0, 270.0, 315.0)
HUB_FLANGE_DOWEL_ANGLES = (0.0, 180.0)
HUB_FLANGE_DOWEL_D = 4.0
HUB_CABLE_D = 9.0
HUB_MASS = 3.15

# DM-J4340-2EC steering actuator, 40:1, 9 Nm rated / 27 Nm peak, 36 rpm rated
STEER_OD = 57.0
STEER_LEN = 53.30
STEER_OUT_PCD = 27.0         # 6 x M3 deep 6, rotating output disc
STEER_OUT_DOWEL_PCD = 25.0   # 2 x d3 H7
STEER_FRONT_PCD = 50.0       # 6 x M3 deep 5, stationary housing, output face
STEER_REAR_PCD = 38.0        # 4 x M3 deep 4, stationary housing, rear face
STEER_REAR_SPIGOT_OD = 35.0
STEER_MASS = 0.33

# DM6540-1EC hub motor driver, one per wheel, mounted in the chassis
DRIVER_L, DRIVER_W, DRIVER_H = 67.0, 51.0, 15.0
DRIVER_HOLE_X, DRIVER_HOLE_Y = 60.5, 44.0

# --------------------------------------------------------------------------
# Chassis top level
# --------------------------------------------------------------------------

# Footprint is solved from the duty case, not styled; see sizing.py.
# Width is capped by the door: 800 rough opening gives under 750 clear, and
# 4WS crabs through sideways, so the narrow side is what has to fit.
WHEELBASE = 560.0            # X, front to rear kingpin axis distance
TRACK = 420.0                # Y, left to right kingpin axis distance

# The body has to be at least the footprint plus the steering sweep, and the
# sweep is whatever the model actually cuts, so derive one from the other
# rather than carrying two numbers that can disagree.
WHEEL_SWEEP_OD = 184.0       # == 2 * SWEEP_CLEAR_R, see below
BODY_L = WHEELBASE + WHEEL_SWEEP_OD  # structure: frame, deck, bays, base plate
BODY_W = TRACK + WHEEL_SWEEP_OD

# Everything underneath lands on one plane: the frame's base plate, the belly
# pan that closes the rest of the footprint, and the bottom edge of the skirt.
# Before this the skirt hung 10 mm below the base plate and the underside was
# open, so the quoted clearance was the skirt edge at 80 while the real belly
# was already 90.  Now the number is the whole flat bottom and nothing hangs
# below it.  Going higher means raising the frame, and with it the deck and
# the centre of gravity, so this is the floor.
GROUND_CLEARANCE = 90.0      # the closed underside, and the true lowest point
DECK_Z = 344.0               # top deck upper face, lift column interface
                             # set so the deck underside clears MODULE_TOP_Z by
                             # more than SUSP_TRAVEL_MECH on full compression

# --------------------------------------------------------------------------
# Corner module, Z stack at nominal ride height
# --------------------------------------------------------------------------

WHEEL_AXIS_Z = HUB_TIRE_OD / 2.0          # 85.5
TIRE_TOP_Z = HUB_TIRE_OD                  # 171.0

YOKE_PLATE_T = 16.0          # vertical plate that bolts to the hub flange
YOKE_TOP_T = 14.0
YOKE_TOP_Z0 = 180.0          # 9 mm clear over the tire
YOKE_TOP_Z1 = YOKE_TOP_Z0 + YOKE_TOP_T    # 194.0

KINGPIN_OD = 50.0            # bearing bore, 6810
KINGPIN_ID = 38.0            # cable duct
KINGPIN_Z0 = YOKE_TOP_Z1     # 194.0
KINGPIN_Z1 = 250.0

BEARING_OD = 65.0            # 6810, 50 x 65 x 7
BEARING_W = 7.0
BEARING_LO_Z = 204.0
BEARING_HI_Z = 236.0         # 32 mm spacing; still ~24x margin on the 6810

HOUSING_L = 104.0            # X
HOUSING_W = 92.0             # Y
HOUSING_Z0 = 202.0
HOUSING_Z1 = 250.0

TUBE_FLANGE_OD = 70.0
TUBE_FLANGE_PCD = 60.0
TUBE_FLANGE_Z0 = KINGPIN_Z1  # 262.0
TUBE_FLANGE_T = 6.0

DIAPHRAGM_OD = 70.0
DIAPHRAGM_T = 3.0
DIAPHRAGM_Z0 = TUBE_FLANGE_Z0 + TUBE_FLANGE_T   # 268.0

STEER_OUT_Z = DIAPHRAGM_Z0 + DIAPHRAGM_T        # 271.0, motor output face
STEER_REAR_Z = STEER_OUT_Z + STEER_LEN          # 324.3
STEER_BRACKET_HALF_X = 32.0  # narrowed so the springs pass outboard of it
STEER_BRACKET_T = 12.0
MODULE_TOP_Z = STEER_REAR_Z + STEER_BRACKET_T   # 336.3

STEER_LIMIT_DEG = 100.0      # cable twist limit, +/- about straight ahead

# --------------------------------------------------------------------------
# Corner suspension, sliding pillar, deliberately stiff and short travel
# --------------------------------------------------------------------------

SUSP_TRAVEL_NOMINAL = 5.0    # +/- mm, working range on an indoor floor
SUSP_TRAVEL_MECH = 12.0      # +/- mm, rail capability, impact reserve
                             # 2.4x the working range; every mm of it is a mm
                             # of deck height, because the deck is the spring seat
SUSP_RATE = 44.0             # N/mm per corner, 1/4 curb weight -> 5 mm
RAIL_LEN = 110.0
RAIL_PITCH_X = 72.0          # two MGN12 rails straddling the kingpin
RAIL_Z0 = 196.0              # must clear the yoke sweep, which tops out at 194
RAIL_Y = -65.0               # local, rail body spans -71..-59; carriage -59..-46
# Two springs and two load cells per corner, straddling the kingpin at y = 0.
# A single offset spring puts its force times its offset onto the rail
# carriages as a moment; that normal load is what makes them stick, and the
# stiction band is what limits how well the chassis can weigh itself.  See
# error_budget.py: this placement cuts the band from 5.9 N to 2.1 N.
SUSP_SPRING_Y = 0.0
SUSP_SPRING_X = 52.0         # local, two off at -X and +X
SUSP_CELLS_PER_CORNER = 2

# Everything below YOKE_SWEEP_Z turns with the wheel.  No frame or shell
# material may enter a cylinder of this radius about any kingpin axis.
YOKE_SWEEP_R = 74.6          # yoke corner, max radius about the kingpin
SWEEP_CLEAR_R = WHEEL_SWEEP_OD / 2   # governed by the tire, 85.5 plus clearance
SWEEP_CLEAR_Z = 200.0

SPINE_Y = TRACK / 2 - 75.0   # side rail plate centreline, carries the MGN rails
SPINE_T = 8.0                # the box is ~25000x stiffer than the load needs;
                             # see frame_budget.py before thickening this again
CROSS_X = 155.0              # cross members frame the lift column interface, so
                             # the column moment goes straight into the webs
                             # instead of bending the bare deck plate
LOADCELL_RANGE_KG = 50.0
LOADCELL_OD = 36.0
LOADCELL_H = 30.0
SPRING_OD = 32.0

# --------------------------------------------------------------------------
# Frame
# --------------------------------------------------------------------------

SHELL_DENSITY = 2.70e-6      # kg/mm^3; the skin is 1.5 mm aluminium now,
                             # folded from flat sheet, not moulded plastic
ALU_DENSITY = 2.70e-6        # kg/mm^3, 6061-T6

BASE_PLATE_T = 6.0
BASE_PLATE_Z0 = GROUND_CLEARANCE + 1.5    # sits on the belly pan, which
                                          # is therefore the only bottom
                                          # surface: the base plate keeps
                                          # its lightening holes and the
                                          # underside is still sealed
BASE_PLATE_L = BODY_L - 120.0
BASE_PLATE_W = 2 * SPINE_Y + 24.0

CORNER_BRACKET_T = 12.0
TOP_PLATE_T = 6.0

# Lift column interface on the deck.  Proposed here so the upper body has a
# fixed thing to design against; change it in one place if the column needs
# something else.  8 x M8 on PCD 200 sees only ~190 N per bolt at 75 Nm.
COLUMN_PCD = 200.0
COLUMN_BOLTS = 8
COLUMN_SPIGOT_OD = 120.0
COLUMN_PAD = 160.0           # half width of the solid, unlightened deck pad
COLUMN_DOUBLER = 260.0       # doubler under the deck; local thickness goes to
COLUMN_DOUBLER_T = 6.0       # 12 mm, which is an 8x cut in local plate bending
TOP_PLATE_Z0 = DECK_Z - TOP_PLATE_T

# Side bays: between the spines and the body sides, between the two sweep
# circles.  14.3 L each and previously empty, which is why the electronics
# hung under the deck.  Boxes bolt to the outboard face of each spine, so no
# extra floor structure is needed.
ELEC_L, ELEC_W, ELEC_H = 300.0, 110.0, 160.0
ELEC_MASS = 2.0

# Deck plate, referenced by the shell so the skin never clips it.
DECK_L = BODY_L - 40.0
DECK_W = BODY_W - 160.0

# --------------------------------------------------------------------------
# Shell: 1.5 mm aluminium, laser cut and folded.  A tapered box is a
# developable surface, so the hip taper costs nothing in tooling.  The taper is
# almost all in Y: seen from the front the body narrows going up, seen from the
# side it is near straight, which is what reads as hips rather than a cart.
# --------------------------------------------------------------------------

# Three volumes stacked, after the Ranger Air language: a dark skirt carrying
# the wheel arches, a recessed belt that is both the parting line and the light
# strip, a light upper shell with a strong shoulder taper, and a dark cover on
# the deck inset from the shell edge.  The parting line is the design line.

SHELL_T = 1.5
SHELL_FILLET = 62.0                  # big soft radii; the body reads as one
                                     # pebble, not a box with rounded corners
SHELL_SKIRT_TOP = 206.0
SHELL_BELT_TOP = 232.0               # 26 mm band, tall enough to be the graphic
SHELL_BELT_OUT = 6.0                 # the band stands proud, it does not recess
SHELL_BOTTOM_TUCK = 16.0             # draft on the lower body; the aft pack
                                     # sets the limit, see build.py THROUGH_SHELL

# Axiom language, after the service robots aboard the ship: one white volume,
# no visible fasteners, and a single dark glossy band doing every job at once.
# That band is the visor, the light strip and the bumper in one part, which is
# why it is allowed to be the only interruption in the surface.
ARCH_LIP = 4.0                       # rolled hem; kills the sheared edge quietly
ARCH_LIP_W = 10.0
COVER_T = 1.5
# The top is white shell with a dark pad let into it, not a black slab laid on
# top.  The upper shell returns inward at deck height, which closes the 30 mm
# slot that otherwise runs down each side between the deck plate and the skin,
# and stiffens the free edge of a 1.5 mm sheet at the same time.  The pad only
# has to clear the column bolt circle and the lifting eyes.
COVER_L = 460.0
COVER_W = 340.0
COVER_R = 100.0
COVER_GAP = 1.0                      # shadow line between pad and flange
# The skin is longer than the structure.  Cut flush with the sweep circles the
# way it was, the four corners are missing and the machine reads as a box on
# legs; carried 60 mm past them, each wheel sits in an opening in a continuous
# flank instead.  Only the skin grows - the frame, deck and bays stay put, so
# nothing about stiffness, mass distribution or the bays moves with it.
#
# Length is free here: the door is passed by crabbing and what it measures is
# the width (see sizing.py), which is untouched at 616.  What does move is the
# diagonal, 966 -> 1053, still inside a 1200 corridor for a spin in place.
SKIRT_BOTTOM_Z = GROUND_CLEARANCE

# Wheel arch, drawn rather than fallen out of a boolean.  Cut by the bare
# steering sweep the opening was a vesica: the sweep cylinder runs tangent to
# the skirt at the top, so the hole closed to a point at the skirt top edge.
#
# What the skin actually has to clear is much less than the sweep itself,
# because the skirt stands 50 mm outboard of the wheel: +-52 mm at the bottom
# edge, narrowing upward, and nothing at all above 183 (the tire crown at full
# bump).  Over that envelope the worst case needs R 99.6 about the wheel axis,
# so a car arch at R 105 contains it with margin and leaves a real crown under
# the band.
# Centred above the axle, the way a car arch is, so the lower lip closes in on
# the tire instead of standing off it: at the skirt's bottom edge the arch is
# narrower than the tire, which is what covering the wheel means.  Centred on
# the axle it needed R 105 and left a 19.5 mm crescent all the way round.
ARCH_CZ = WHEEL_AXIS_Z + 9.5
ARCH_R = 95.0
ARCH_INNER_Y = 200.0                 # the arch runs in behind the wheel, so the
                                     # step down to the sweep cylinder is hidden
ARCH_LINER_T = 2.0
BELLY_PAN_T = 1.5

# The arch stands proud of the side instead of being a hole cut in it: a band
# following the arch, raised off the surface the way a car's wheel arch is.
# Width is measured radially about the wheel axis in side view and the lift is
# normal to the skin, so unlike a band of constant width in plan it cannot
# turn into a sail where the surface runs away from it.  The front flare
# reaches 27 mm into the 62 mm body corner, where the surface still runs 0.90
# along X, so it wraps the corner at 24 mm wide rather than blowing out.
FLARE_W = 26.0                       # radial width outward from the arch lip
FLARE_OUT = 6.0                      # how far it stands off the skin
assert FLARE_OUT <= SHELL_BELT_OUT, "flare would outgrow the bumper band"

# The arch is drawn, not derived, so both sides of it are asserted.  Build.py
# additionally sweeps the tire through bump and lock against the modelled well.
_tire_bump = WHEEL_AXIS_Z + SUSP_TRAVEL_MECH
_tire_corner = math.hypot(HUB_TREAD_W / 2, HUB_TIRE_OD / 2)   # at 90 deg lock
assert ARCH_R - (abs(_tire_bump - ARCH_CZ) + _tire_corner) >= 3.0, (
    "arch fouls the tire at full bump and lock: %.1f mm"
    % (ARCH_R - (abs(_tire_bump - ARCH_CZ) + _tire_corner)))
SHELL_OVERHANG = 60.0
SHELL_L = BODY_L + 2 * SHELL_OVERHANG

# The white volume drafts gently and then rolls over into the roof, instead of
# meeting it at a hard arris.  The previous 50 mm a side, in Y only, was a 24
# degree wedge and read as a lid rather than as a body; 14 mm over the 99 mm of
# straight flank is 8 degrees, and the last 14 mm is the roll.
SHELL_SHOULDER = 14.0                # straight draft, per side
SHELL_CROWN = 14.0                   # radius of the roll into the roof
SHELL_TOP_L = SHELL_L - 2 * (SHELL_SHOULDER + SHELL_CROWN)
BODY_W_MAX = BODY_W + 2 * SHELL_BELT_OUT

# Real requirements that the skin has to carry, not styling.  Nav2 needs a
# scanner; one 270 degree unit cannot see behind itself, so two sit at
# diagonal corners, which is the ordinary AMR answer and happens to give the
# band something to do.  A 100 kg machine needs lifting points, and they bolt
# to the frame nodes where a spine meets a cross member, not to the skin.
LIDAR_CORNERS = ("FL", "RR")
LIDAR_FOV = 150.0                    # window half angle each side of diagonal
CAM_W = 120.0                        # forward depth camera window
LIFT_EYE_OD = 30.0
LIFT_EYE_XY = (CROSS_X, SPINE_Y)     # spine meets cross member: a real node

# How far the waist can pull in is set by the corner modules, not by taste: the
# steering motor bracket reaches TRACK/2 + HOUSING_W/2 at MODULE_TOP_Z and the
# skin has to stay outside it.  Derived so the taper can never quietly grow
# back into a module.
_SHELL_F = (MODULE_TOP_Z - SHELL_BELT_TOP) / (DECK_Z - SHELL_BELT_TOP)
_SHELL_NEED = TRACK / 2 + HOUSING_W / 2 + 5.0
_SHELL_TOP_W_MIN = BODY_W - (BODY_W - 2 * _SHELL_NEED) / _SHELL_F
SHELL_TOP_W = BODY_W - 2 * (SHELL_SHOULDER + SHELL_CROWN)
assert SHELL_TOP_W >= _SHELL_TOP_W_MIN, (
    "upper shell drafts past the corner module envelope: %.0f < %.0f"
    % (SHELL_TOP_W, _SHELL_TOP_W_MIN))
assert SHELL_TOP_L >= DECK_L + 6.0, "upper shell drafts inside the deck plate"
ESTOP_OD = 40.0
ESTOP_Z = 300.0
IO_PANEL = (150.0, 40.0)             # charge port, switch, ethernet, status

LIGHTEN_PITCH = 78.0
LIGHTEN_D = 64.0
WEB_HOLE_D = 100.0           # truss holes in the spines and cross members
WEB_HOLE_PITCH = 150.0

# --------------------------------------------------------------------------
# Battery layout.  Two arrangements are carried side by side so they can be
# compared as built rather than argued about:
#
#   rear  one pack in the aft bay.  Puts the chassis centre of gravity 38 mm
#         back, which is worth 0.29 of forward safety factor for free.
#   side  two packs in the belly flanks, G2 style.  Symmetric, 28 percent less
#         polar inertia, lower, and it gives the shell a waist to wrap.
#
#   STEM_BATTERY=side python build.py
# --------------------------------------------------------------------------

BATTERY_LAYOUT = os.environ.get("STEM_BATTERY", "rear").lower()
assert BATTERY_LAYOUT in ("rear", "side"), BATTERY_LAYOUT
EXPORT_DIR = "export/" + BATTERY_LAYOUT

BATTERY_MASS = 8.0
REAR_BAY_X = -(CROSS_X + SPINE_T / 2 + (BODY_L / 2 - 10.0)) / 2

if BATTERY_LAYOUT == "rear":
    # One pack, aft bay.  The bay is waisted, not rectangular: the two rear
    # sweep circles pinch the clear width from 262 to 236 at the axle line, so
    # the pack is sized on the narrow point.  build.py checks it.
    BATTERY_L, BATTERY_W, BATTERY_H = 190.0, 220.0, 200.0
    BATTERY_PACKS = [(REAR_BAY_X, 0.0)]
    ELEC_L, ELEC_W, ELEC_H = 300.0, 110.0, 160.0
    ELEC_SIDE = True             # electronics in the belly flanks
else:
    # Two packs in the belly flanks, hung off the outboard face of each spine.
    # Nothing supports them from below out there, which is fine: a flank pack
    # is a plate hanging on the web, not a box sitting on a floor.
    BATTERY_L, BATTERY_W, BATTERY_H = 300.0, 120.0, 170.0
    BATTERY_PACKS = []           # filled in below once SPINE_Y is known
    ELEC_L, ELEC_W, ELEC_H = 170.0, 225.0, 150.0
    ELEC_SIDE = False            # electronics take the aft bay instead

BATTERY_X = BATTERY_PACKS[0][0] if BATTERY_PACKS else 0.0
# Deck cut-out over each equipment bay.  Sized to stay clear of the cross
# member and the spines, so it never interrupts a load path.  It is for
# electronics access: the battery is wider than the gap between the spines and
# comes out of the back of the shell instead.
_BAY_L = BODY_L / 2 - 10.0 - (CROSS_X + SPINE_T / 2)
SERVICE_OPENING = (_BAY_L - 24.0, 2 * SPINE_Y - 40.0)

# --------------------------------------------------------------------------
# Mass budget used for the stability check
# --------------------------------------------------------------------------

MASS = {
    "hub_motors": 4 * HUB_MASS,
    "steer_motors": 4 * STEER_MASS,
    "drivers_harness": 1.5,
    "battery": BATTERY_MASS,
    "frame": 16.0,
    "shell": 4.0,
    "suspension": 4 * 1.2,
    "electronics": 2.0,
}
# --------------------------------------------------------------------------
# Upper body, estimated 2026-10-07.  Inputs given: robot 1.4 to 1.6 m tall,
# arm span 1.4 to 1.5 m, compute and switch in the chest.  Itemised so each
# line can be argued with and replaced as the upper body is actually designed.
# This is the largest remaining uncertainty in the whole size chain.
# --------------------------------------------------------------------------

ARM_SPAN = 1450.0
SHOULDER_W = 400.0
ARM_LEN = (ARM_SPAN - SHOULDER_W) / 2        # 525, shoulder to fingertip
SHOULDER_Z = 1350.0                          # lift fully extended, worst case

UPPER_BODY = {                               # name: (mass kg, cog height mm)
    "lift_column": (14.0, 800.0),            # 3 stage, rails + screw + motor
    "chest": (8.0, 1150.0),                  # structure, compute, switch, PDU
    "arms": (13.0, 1300.0),                  # two arms incl. grippers
    "head": (2.0, 1480.0),                   # cameras and pan tilt
}
UPPER_BODY_MASS = sum(m for m, _ in UPPER_BODY.values())
UPPER_BODY_COG_Z = sum(m * z for m, z in UPPER_BODY.values()) / UPPER_BODY_MASS
ARM_MASS = UPPER_BODY["arms"][0]

PAYLOAD_MASS = 5.0
PAYLOAD_Z = SHOULDER_Z

# Reach is geometry, not a guess: it falls out of the arm span.
ARM_REACH_FWD = ARM_LEN + 25                 # 550, payload offset from centre
ARM_REACH_LAT = SHOULDER_W / 2 + ARM_LEN     # 725, one fingertip from centre
LAT_ARM_FRACTION = 0.5                       # one arm sideways; both arms to
                                             # one side is left to the envelope
LAT_DESIGN_REACH = 400.0                     # comfortable working reach while
                                             # crabbing.  Full 725 reach and
                                             # full crab acceleration never
                                             # happen together, so sizing on
                                             # both at once double counts.

ESTOP_DECEL = 1.0            # m/s^2, commanded emergency ramp.  This number is
                             # only valid because the stop circuit is Cat-1 and
                             # never shorts the motor phases; see the ADR.
                             # Shorting a direct drive H65 gives about 9.9 m/s^2,
                             # which tips the robot at any wheelbase we would build.
LATERAL_ACCEL = 0.7          # m/s^2
FLOOR_SLOPE_DEG = 3.0

# --------------------------------------------------------------------------
# Derived performance, 24 V
# --------------------------------------------------------------------------

ROLLING_R = HUB_TIRE_OD / 2000.0        # metres, 0.0855
V_RATED = 120.0 / 60.0 * 2 * 3.141592653589793 * ROLLING_R   # m/s
V_MAX_NOLOAD = 260.0 / 60.0 * 2 * 3.141592653589793 * ROLLING_R
F_TRACTIVE_RATED = 4 * 6.0 / ROLLING_R  # N
F_TRACTIVE_PEAK = 4 * 21.5 / ROLLING_R
I_BUS_RATED = 4 * 5.10                  # A at 24 V
I_BUS_PEAK = 4 * 21.55

CORNERS = (
    ("FL", +WHEELBASE / 2, +TRACK / 2),
    ("FR", +WHEELBASE / 2, -TRACK / 2),
    ("RL", -WHEELBASE / 2, +TRACK / 2),
    ("RR", -WHEELBASE / 2, -TRACK / 2),
)

# --------------------------------------------------------------------------
# Deferred placements that need SPINE_Y
# --------------------------------------------------------------------------

_FLANK_Y = SPINE_Y + SPINE_T / 2

if BATTERY_LAYOUT == "side":
    BATTERY_PACKS = [(0.0, _FLANK_Y + BATTERY_W / 2),
                     (0.0, -(_FLANK_Y + BATTERY_W / 2))]
    BATTERY_Z0 = GROUND_CLEARANCE + 10.0        # as low as the skirt allows
    ELEC_PACKS = [(REAR_BAY_X, 0.0)]
    ELEC_Z0 = BASE_PLATE_Z0 + BASE_PLATE_T
else:
    BATTERY_Z0 = BASE_PLATE_Z0 + BASE_PLATE_T
    ELEC_PACKS = [(0.0, _FLANK_Y + ELEC_W / 2), (0.0, -(_FLANK_Y + ELEC_W / 2))]
    ELEC_Z0 = BASE_PLATE_Z0 + 14.0
