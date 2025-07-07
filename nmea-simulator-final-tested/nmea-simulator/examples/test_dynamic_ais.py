import sys
import os
import time
import logging
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator.core.enhanced_engine import EnhancedSimulationEngine, SimulationConfig
from simulator.generators.vessel import create_default_vessel_config
from nmea_lib.types import Position
from simulator.outputs.base import OutputHandler

# Configure logging to see engine output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# Custom output handler to print AIVDM messages
class ConsoleAIVDMOutput(OutputHandler):
    def send_sentence(self, sentence: str) -> bool:
        if sentence.startswith("!AIVDM"):
            print(f"AIS: {sentence.strip()}")
        return True

    def start(self):
        print("ConsoleAIVDMOutput started.")

    def stop(self):
        print("ConsoleAIVDMOutput stopped.")

    def close(self):
        print("ConsoleAIVDMOutput closed.")

def run_dynamic_ais_test():
    print("Starting dynamic AIS test...")

    # 1. Create SimulationConfig
    sim_config = SimulationConfig(
        duration=20.0,  # Run for 20 seconds
        update_interval=1.0,  # Vessel state update interval
        gps_update_interval=1.0, # GPS generation (not primary focus here)
        ais_update_interval=0.5, # How often AIS scheduler is checked
        enable_gps=True, # Enable GPS to have some NMEA traffic
        enable_ais=True,
        log_level="INFO"
    )

    # 2. Create EnhancedSimulationEngine
    engine = EnhancedSimulationEngine(sim_config)

    # 3. Add a custom output handler
    console_handler = ConsoleAIVDMOutput()
    engine.add_output_handler(console_handler)

    # 4. Add a vessel
    vessel_mmsi = 227000001
    initial_pos = Position(latitude=40.7128, longitude=-74.0060) # NYC

    # Use a default config and then potentially modify if needed
    vessel_config_dict = create_default_vessel_config(
        mmsi=vessel_mmsi,
        name="DYNAMIC TESTER",
        position=initial_pos,
        vessel_class='A'
    )
    # Ensure initial speed and heading are something that will lead to movement
    vessel_config_dict['initial_speed'] = 10.0 # knots
    vessel_config_dict['initial_heading'] = 45.0 # degrees
    vessel_config_dict['movement']['speed_variation'] = 0.5 # knots, for the new random walk
    vessel_config_dict['movement']['course_variation'] = 5.0 # degrees, for the new random walk

    # Modify the EnhancedVesselGenerator's course_change_interval for more frequent course changes
    # This is not directly settable via vessel_config_dict for EnhancedVesselGenerator,
    # but my SOG/COG changes are now random walks per update, so this might be less critical.
    # The default course_change_interval in EnhancedVesselGenerator is 5 mins, which is too long for a 20s test.
    # My change makes COG vary per _apply_movement_variation call if current_time - self.last_course_change > self.course_change_interval
    # Let's make the interval shorter in the generator or rely on the random walk.
    # The current _apply_movement_variation has:
    # if current_time - self.last_course_change > self.course_change_interval:
    #    course_change_amount = self.rng.uniform(-10.0, 10.0) # degrees
    #    nav.cog = (nav.cog + course_change_amount) % 360.0
    # For a 20s test, 5 min interval means it won't trigger.
    # I will rely on the fact that my modified `_apply_movement_variation` in `EnhancedVesselGenerator`
    # now updates SOG and COG on every call to `update_vessel_state` via random walk,
    # which `EnhancedSimulationEngine` calls at `config.update_interval`.

    engine.add_vessel(vessel_config_dict)

    # 5. Start the engine
    engine.start()
    print(f"Engine started. Running for {sim_config.duration} seconds...")

    # 6. Wait for completion
    start_time = time.time()
    while engine.is_running():
        if time.time() - start_time > (sim_config.duration + 5): # Timeout guard
            print("Test timed out, stopping engine.")
            break
        try:
            time.sleep(0.5)
            # Periodically print some high-level state if desired
            # vessel_states = engine.get_vessel_states()
            # if vessel_mmsi in vessel_states:
            #     current_v_state = vessel_states[vessel_mmsi].navigation_data
            #     print(f"Time: {time.time() - start_time:.1f}s - Vessel {vessel_mmsi} SOG: {current_v_state.sog:.2f}, COG: {current_v_state.cog:.2f}, ROT: {current_v_state.rot}, Pos: {current_v_state.position.latitude:.4f},{current_v_state.position.longitude:.4f}")
        except KeyboardInterrupt:
            print("Keyboard interrupt received.")
            break

    engine.stop()
    print("Engine stopped.")
    print("Dynamic AIS test finished.")

if __name__ == "__main__":
    run_dynamic_ais_test()
