import unittest
from datetime import datetime, timedelta

# Add project root to allow imports from simulator and nmea_lib
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.generators.vessel import EnhancedVesselGenerator, create_default_vessel_config
from nmea_lib.types import Position
from nmea_lib.ais.constants import NavigationStatus

class TestEnhancedVesselGenerator(unittest.TestCase):
    """Tests for the EnhancedVesselGenerator."""

    def test_dynamic_sog_cog_rot_and_navstatus(self):
        """Test that SOG, COG, ROT, and NavStatus change dynamically and correctly."""
        initial_pos = Position(latitude=40.0, longitude=-70.0)
        vessel_config = create_default_vessel_config(
            mmsi=123456789,
            name="Dynamic Test Ship",
            position=initial_pos
        )
        vessel_config['initial_speed'] = 10.0
        vessel_config['initial_heading'] = 90.0
        vessel_config['movement']['speed_variation'] = 0.5
        vessel_config['movement']['course_variation'] = 10.0
        # Default max_speed in create_default_vessel_config is not set,
        # my generator code uses self.vessel_config.get('max_speed', 25.0)
        # So, max_speed is 25.0 by default.

        generator = EnhancedVesselGenerator(vessel_config)

        # --- Test SOG Dynamism ---
        sog_initial_nav_data = generator.get_current_state().navigation_data
        initial_sog = sog_initial_nav_data.sog
        initial_pos_for_sog_test = sog_initial_nav_data.position

        time_step_seconds = 1.0
        sog_test_time = datetime.utcnow()

        sog_test_time += timedelta(seconds=time_step_seconds)
        sog_state2_nav = generator.update_vessel_state(time_step_seconds, sog_test_time).navigation_data

        sog_test_time += timedelta(seconds=time_step_seconds)
        sog_state3_nav = generator.update_vessel_state(time_step_seconds, sog_test_time).navigation_data

        sog_changed_from_initial_at_step2 = abs(sog_state2_nav.sog - initial_sog) > 0.001
        sog_changed_from_step2_at_step3 = abs(sog_state3_nav.sog - sog_state2_nav.sog) > 0.001
        sog_changed_from_initial_at_step3 = abs(sog_state3_nav.sog - initial_sog) > 0.001

        self.assertTrue(sog_changed_from_initial_at_step2 or \
                        sog_changed_from_step2_at_step3 or \
                        sog_changed_from_initial_at_step3,
                        f"SOG should show some variation. initial={initial_sog:.3f}, s2={sog_state2_nav.sog:.3f}, s3={sog_state3_nav.sog:.3f}")

        self.assertNotEqual(initial_pos_for_sog_test, sog_state3_nav.position, "Position should change during SOG updates")

        # --- Test COG and ROT Dynamism & Logic ---
        generator.course_change_interval = timedelta(seconds=1.0)
        sim_time_t0 = datetime.utcnow()

        generator.last_course_change = sim_time_t0 - generator.course_change_interval - timedelta(seconds=0.1)

        elapsed_s0 = 0.1
        s0_nav_data = generator.update_vessel_state(elapsed_seconds=elapsed_s0, current_time=sim_time_t0).navigation_data
        cog_s0 = s0_nav_data.cog
        pos_s0 = s0_nav_data.position
        self.assertEqual(generator.last_course_change, sim_time_t0)

        elapsed_s1 = 0.5
        sim_time_t1 = sim_time_t0 + timedelta(seconds=elapsed_s1)
        s1_nav_data = generator.update_vessel_state(elapsed_seconds=elapsed_s1, current_time=sim_time_t1).navigation_data
        cog_s1 = s1_nav_data.cog
        rot_s1 = s1_nav_data.rot

        self.assertAlmostEqual(cog_s1, cog_s0, places=3,
                               msg=f"COG should not change if interval not passed. COG_s0={cog_s0:.3f}, COG_s1={cog_s1:.3f}")
        self.assertEqual(generator.last_course_change, sim_time_t0, "last_course_change should remain t0.")

        cog_diff_s0_to_s1 = cog_s1 - cog_s0
        if cog_diff_s0_to_s1 > 180: cog_diff_s0_to_s1 -= 360
        if cog_diff_s0_to_s1 < -180: cog_diff_s0_to_s1 += 360
        expected_rot_s1 = int(round((cog_diff_s0_to_s1 / elapsed_s1) * 60.0)) if elapsed_s1 > 0 else 0
        self.assertEqual(rot_s1, expected_rot_s1,
                               msg=f"ROT for s1. cog_s0={cog_s0:.2f}, cog_s1={cog_s1:.2f}. Rot={rot_s1}, Expected={expected_rot_s1}")

        elapsed_s2 = 0.6
        sim_time_t2 = sim_time_t1 + timedelta(seconds=elapsed_s2)
        s2_nav_data = generator.update_vessel_state(elapsed_seconds=elapsed_s2, current_time=sim_time_t2).navigation_data
        cog_s2 = s2_nav_data.cog
        rot_s2 = s2_nav_data.rot
        pos_s2 = s2_nav_data.position

        self.assertEqual(generator.last_course_change, sim_time_t2)
        self.assertTrue(abs(cog_s2 - cog_s1) > 0.001 or rot_s2 != 0, # COG changed OR ROT is non-zero (implies COG changed)
                        f"COG should have attempted update (or ROT reflects it). cog_s1={cog_s1:.3f}, cog_s2={cog_s2:.3f}, rot_s2={rot_s2}")

        cog_diff_s1_to_s2 = cog_s2 - cog_s1
        if cog_diff_s1_to_s2 > 180: cog_diff_s1_to_s2 -= 360
        if cog_diff_s1_to_s2 < -180: cog_diff_s1_to_s2 += 360
        expected_rot_s2 = int(round((cog_diff_s1_to_s2 / elapsed_s2) * 60.0)) if elapsed_s2 > 0 else 0
        self.assertEqual(rot_s2, expected_rot_s2,
                         msg=f"ROT for s2. cog_s1={cog_s1:.2f}, cog_s2={cog_s2:.2f}. Rot={rot_s2}, Expected={expected_rot_s2}")

        self.assertNotEqual(pos_s0, pos_s2, "Position should change over COG/ROT test updates")

        # --- Test NavStatus Update ---
        time_now_for_nav_status = datetime.utcnow()
        anchor_config = create_default_vessel_config(mmsi=1, name="Anchor", position=initial_pos)
        anchor_config['initial_speed'] = 0.02
        anchor_gen = EnhancedVesselGenerator(anchor_config)
        anchor_nav = anchor_gen.update_vessel_state(1.0, time_now_for_nav_status).navigation_data
        if anchor_nav.sog < 0.1:
            self.assertEqual(anchor_nav.nav_status, NavigationStatus.AT_ANCHOR, f"NavStatus AT_ANCHOR for SOG {anchor_nav.sog:.3f}")
        else:
            self.assertEqual(anchor_nav.nav_status, NavigationStatus.UNDER_WAY_USING_ENGINE, f"NavStatus UNDER_WAY for SOG {anchor_nav.sog:.3f} (anchor test)")

        moving_config = create_default_vessel_config(mmsi=2, name="Moving", position=initial_pos)
        moving_config['initial_speed'] = 5.0
        moving_gen = EnhancedVesselGenerator(moving_config)
        moving_nav = moving_gen.update_vessel_state(1.0, time_now_for_nav_status).navigation_data
        # SOG will be around 5.0 +/- 0.5. This range is 0.1 <= SOG <= 23.0
        self.assertEqual(moving_nav.nav_status, NavigationStatus.UNDER_WAY_USING_ENGINE, f"NavStatus UNDER_WAY for SOG={moving_nav.sog:.2f}")

        high_speed_config = create_default_vessel_config(mmsi=3, name="HighSpeed", position=initial_pos)
        high_speed_config['initial_speed'] = 25.0
        high_speed_gen = EnhancedVesselGenerator(high_speed_config)
        high_speed_nav = high_speed_gen.update_vessel_state(1.0, time_now_for_nav_status).navigation_data
        # SOG will be around 25.0 +/- 0.5. This should be > 23.0
        self.assertEqual(high_speed_nav.nav_status, NavigationStatus.UNDER_WAY_USING_ENGINE, f"NavStatus UNDER_WAY for SOG={high_speed_nav.sog:.2f} (High Speed)")

if __name__ == '__main__':
    unittest.main()
