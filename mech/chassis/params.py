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

WHEELBASE = 700.0            # X, front to rear kingpin axis distance
TRACK = 500.0                # Y, left to right kingpin axis distance

WHEEL_SWEEP_OD = 180.0       # tire OD plus clearance, governs corner cut-outs
BODY_L = WHEELBASE + WHEEL_SWEEP_OD
BODY_W = TRACK + WHEEL_SWEEP_OD

GROUND_CLEARANCE = 60.0      # skirt underside
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
SWEEP_CLEAR_R = 92.0         # governed by the tire, 85.5 plus clearance
SWEEP_CLEAR_Z = 200.0

SPINE_Y = 173.0              # side rail plate centreline, carries the MGN rails
SPINE_T = 12.0
LOADCELL_RANGE_KG = 50.0
LOADCELL_OD = 36.0
LOADCELL_H = 30.0
SPRING_OD = 32.0

# --------------------------------------------------------------------------
# Frame
# --------------------------------------------------------------------------

SHELL_T = 2.0                # non structural skin, PC or ABS sheet
SHELL_DENSITY = 1.20e-6      # kg/mm^3
ALU_DENSITY = 2.70e-6        # kg/mm^3, 6061-T6

BASE_PLATE_T = 6.0
BASE_PLATE_Z0 = 70.0         # 10 mm above the skirt; the old 100 was dead air
BASE_PLATE_L = 640.0
BASE_PLATE_W = 440.0

CORNER_BRACKET_T = 12.0
TOP_PLATE_T = 6.0
TOP_PLATE_Z0 = DECK_Z - TOP_PLATE_T

LIGHTEN_PITCH = 78.0
LIGHTEN_D = 64.0
WEB_HOLE_D = 100.0           # truss holes in the spines and cross members
WEB_HOLE_PITCH = 150.0

BATTERY_L, BATTERY_W, BATTERY_H = 260.0, 180.0, 210.0   # 24V 30Ah LiFePO4
BATTERY_MASS = 8.0

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
UPPER_BODY_MASS = 40.0
UPPER_BODY_COG_Z = 0.80 * 1000.0
PAYLOAD_MASS = 5.0
ARM_REACH_FWD = 700.0
ARM_REACH_LAT = 450.0
PAYLOAD_Z = 1400.0

ESTOP_DECEL = 1.5            # m/s^2, commanded emergency ramp
LATERAL_ACCEL = 1.0          # m/s^2
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
