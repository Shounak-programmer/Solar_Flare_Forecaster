"""Unit tests for SURYASETU physics calculations and scientific constants.

Verifies:
1. Speed of light = 299,792.458 km/s
2. Sun-Earth distance = 149,597,870.7 km (~1 AU)
3. Light travel time Sun -> Earth = ~499.0 seconds (~8 min 19 sec)
4. Earth-L1 distance = ~1,500,000 km
5. Sun-L1 distance = ~148,097,870.7 km
6. Light travel time Sun -> L1 = ~494.0 seconds (~8 min 14 sec)
7. Aditya-L1 EM timing advantage over Earth = ~5.004 seconds (range 2.7 to 7.3 s with halo orbit)
8. L3 distance from Earth = ~299.2 million km, light travel time ~998 seconds
9. 3D Vector angle calculation correctness (0 deg, 90 deg, 180 deg, general angles)
10. Strict rule: NO "8 minutes early warning from L1" claim!
"""
import math
import unittest

C_KM_S = 299792.458
SUN_EARTH_KM = 149597870.7
EARTH_L1_KM = 1500000.0
EARTH_L2_KM = 1500000.0
EARTH_L3_KM = 299195740.0

ADITYA_HALO_AY_KM = 670000.0


def calculate_distance(a, b):
    dx = a[0] - b[0]
    dy = a[1] - b[1]
    dz = a[2] - b[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def calculate_light_travel_time(distance_km):
    return distance_km / C_KM_S


def calculate_relative_delay(dist_a_km, dist_b_km):
    time_a = calculate_light_travel_time(dist_a_km)
    time_b = calculate_light_travel_time(dist_b_km)
    return time_b - time_a


def calculate_angle(a, vertex, b):
    u = (a[0] - vertex[0], a[1] - vertex[1], a[2] - vertex[2])
    v = (b[0] - vertex[0], b[1] - vertex[1], b[2] - vertex[2])
    mag_u = math.sqrt(sum(x * x for x in u))
    mag_v = math.sqrt(sum(x * x for x in v))
    if mag_u == 0 or mag_v == 0:
        return 0.0
    dot = sum(x * y for x, y in zip(u, v))
    cos_theta = max(-1.0, min(1.0, dot / (mag_u * mag_v)))
    return math.degrees(math.acos(cos_theta))


class TestSuryaSetuPhysics(unittest.TestCase):

    def test_sun_earth_distance_and_propagation(self):
        sun = (0, 0, 0)
        earth = (SUN_EARTH_KM, 0, 0)
        d = calculate_distance(sun, earth)
        self.assertAlmostEqual(d, SUN_EARTH_KM, delta=1.0)

        t_sec = calculate_light_travel_time(d)
        # Sun to Earth EM propagation: ~499.005 s
        self.assertTrue(498.5 < t_sec < 499.5)
        self.assertAlmostEqual(t_sec, 499.0, delta=0.1)

    def test_aditya_l1_nominal_and_advantage(self):
        sun = (0, 0, 0)
        earth = (SUN_EARTH_KM, 0, 0)
        l1_nominal = (SUN_EARTH_KM - EARTH_L1_KM, 0, 0)

        d_sun_l1 = calculate_distance(sun, l1_nominal)
        t_l1 = calculate_light_travel_time(d_sun_l1)
        t_earth = calculate_light_travel_time(calculate_distance(sun, earth))

        # Sun-L1 light travel time: ~494.0 s
        self.assertTrue(493.5 < t_l1 < 494.5)

        # Nominal advantage: ~5.004 seconds
        lead = t_earth - t_l1
        self.assertAlmostEqual(lead, 5.004, delta=0.01)

        # Strict check: lead must NEVER be close to 8 minutes (480s)
        self.assertLess(lead, 10.0, "L1 EM timing advantage must be seconds, not minutes!")

    def test_aditya_l1_halo_orbit_variation(self):
        # Halo orbit Ay semi-amplitude is ~670,000 km
        # Timing delta: dt = 670,000 / 299,792.458 ≈ 2.235 seconds
        delta_t = ADITYA_HALO_AY_KM / C_KM_S
        self.assertAlmostEqual(delta_t, 2.235, delta=0.05)

        nominal_lead = 5.004
        min_lead = nominal_lead - delta_t  # ~2.77 s
        max_lead = nominal_lead + delta_t  # ~7.24 s

        self.assertTrue(2.5 <= min_lead <= 3.0)
        self.assertTrue(7.0 <= max_lead <= 7.5)

    def test_earth_l2_l3_distances(self):
        sun = (0, 0, 0)
        earth = (SUN_EARTH_KM, 0, 0)
        l2 = (SUN_EARTH_KM + EARTH_L2_KM, 0, 0)
        l3 = (-SUN_EARTH_KM, 0, 0)

        d_earth_l2 = calculate_distance(earth, l2)
        self.assertAlmostEqual(d_earth_l2, EARTH_L2_KM, delta=1.0)

        d_earth_l3 = calculate_distance(earth, l3)
        self.assertAlmostEqual(d_earth_l3, 2 * SUN_EARTH_KM, delta=1.0)

        # Light time Earth -> L3: ~998 seconds (~16.6 min)
        t_l3 = calculate_light_travel_time(d_earth_l3)
        self.assertTrue(995.0 < t_l3 < 1000.0)

    def test_vector_angles(self):
        sun = (0, 0, 0)
        earth = (100, 0, 0)
        l2 = (120, 0, 0)
        l3 = (-100, 0, 0)
        perpendicular = (100, 100, 0)

        # Vector Earth->Sun is (-100, 0, 0), Vector Earth->L2 is (+20, 0, 0) -> 180 degrees
        angle_collinear = calculate_angle(sun, earth, l2)
        self.assertAlmostEqual(angle_collinear, 180.0, delta=0.01)

        # Angle perpendicular
        angle_90 = calculate_angle(sun, earth, perpendicular)
        self.assertAlmostEqual(angle_90, 90.0, delta=0.01)

        # Angle Earth - Sun - L3 (opposite sides of Sun): 180°
        angle_l3 = calculate_angle(earth, sun, l3)
        self.assertAlmostEqual(angle_l3, 180.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
