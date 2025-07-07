#!/usr/bin/env python3
"""
Simple Working NMEA+AIS Simulator Example - Refactored for Dynamic AIS

This example demonstrates the NMEA simulator with dynamic AIS message generation.
"""

import sys
import os
import json
import time # time.sleep might be useful if running interactively
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nmea_lib.types import Position
# from nmea_lib.types.units import Distance, DistanceUnit # Not directly used after refactor
# from nmea_lib.sentences.gga import GGASentence # Built manually now
# from nmea_lib.sentences.rmc import RMCSentence # Built manually now
from nmea_lib.sentences.aivdm import AISMessageGenerator
from nmea_lib.types.datetime import NMEATime, NMEADate # Used by GPS sentence generation
from nmea_lib.types.vessel import VesselState, VesselClass, ShipType, NavigationStatus # Used by GPS
# from nmea_lib.types import create_vessel_state # Replaced by EnhancedVesselGenerator config

from simulator.generators.vessel import EnhancedVesselGenerator, create_default_vessel_config
from nmea_lib.parser import SentenceBuilder # For GPS sentences
from nmea_lib.base import TalkerId, SentenceId # For GPS sentences


class SimpleNMEASimulator:
    """Simple NMEA simulator with dynamic AIS."""
    
    def __init__(self, output_dir="simple_output_dynamic"):
        """Initialize the simulator."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.vessel_generators: list[EnhancedVesselGenerator] = []
        self.reference_data = []
        self.message_count = 0
        
        # AISMessageGenerator is used to create AIVDM sentences from VesselState
        self.ais_message_generator = AISMessageGenerator()
        
        self._create_dynamic_vessels()
    
    def _create_dynamic_vessels(self):
        """Create dynamic vessel generators."""
        
        # Vessel 1: Dynamic Container ship
        pos1 = Position(37.8000, -122.4000)
        vessel1_config = create_default_vessel_config(
            mmsi=367001234,
            name="DYNAMIC EVER",
            position=pos1,
            vessel_class='A'
        )
        vessel1_config['initial_speed'] = 12.0  # knots
        vessel1_config['initial_heading'] = 75.0 # degrees
        vessel1_config['movement']['speed_variation'] = 0.5
        vessel1_config['movement']['course_variation'] = 10.0
        # Add some static data not in default config if needed by Type 5
        vessel1_config['callsign'] = vessel1_config.get('callsign', f"CALL{vessel1_config['mmsi']%10000}")
        vessel1_config['ship_type'] = vessel1_config.get('ship_type', ShipType.CARGO_ALL_SHIPS)
        vessel1_config['dimensions'] = vessel1_config.get('dimensions', {'to_bow': 150, 'to_stern': 50, 'to_port': 15, 'to_starboard': 15})
        vessel1_config['voyage'] = vessel1_config.get('voyage', {'destination': "OAKLAND", 'draught': 12.5})


        self.vessel_generators.append(EnhancedVesselGenerator(vessel1_config))

        # Could add more vessels here if desired
        # pos2 = Position(37.7500, -122.4500)
        # vessel2_config = create_default_vessel_config(mmsi=367002345, name="DYNAMIC PACIFIC", position=pos2)
        # self.vessel_generators.append(EnhancedVesselGenerator(vessel2_config))

    def generate_scenario(self, duration_minutes=1): # Shortened for easier testing
        """Generate a complete scenario with reference data."""
        
        print(f"Generating {duration_minutes}-minute scenario with {len(self.vessel_generators)} dynamic vessel(s)...")
        
        nmea_file = self.output_dir / "nmea_output_dynamic.txt"
        reference_file = self.output_dir / "reference_data_dynamic.json"
        human_file = self.output_dir / "human_readable_dynamic.txt"
        
        # Use a fixed start time for reproducibility of simulation path if time_factor is involved
        # For this script, current_time is advanced by 1 real second per step.
        sim_current_time = datetime.utcnow()
        sim_start_time = sim_current_time
        sim_end_time = sim_start_time + timedelta(minutes=duration_minutes)
        
        with open(nmea_file, 'w') as nmea_f, open(human_file, 'w') as human_f:
            human_f.write("Dynamic NMEA Simulator Output - Human Readable\n")
            human_f.write("=" * 60 + "\n")
            human_f.write(f"Generated: {sim_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            human_f.write(f"Duration: {duration_minutes} minutes\n")
            human_f.write(f"Vessels: {len(self.vessel_generators)}\n")
            human_f.write("=" * 60 + "\n\n")
            
            step = 0
            time_step_seconds = 1.0 # Each step in the loop represents 1 second of simulated time

            while sim_current_time < sim_end_time:
                step += 1
                
                # Update all vessel states
                for v_gen in self.vessel_generators:
                    v_gen.update_vessel_state(elapsed_seconds=time_step_seconds, current_time=sim_current_time)
                
                # Generate GPS sentences every 5 seconds (for each vessel)
                if step % 5 == 0:
                    for v_gen in self.vessel_generators:
                        vessel_state = v_gen.get_current_state()
                        gps_sentences = self._generate_gps_sentences(vessel_state, sim_current_time)
                        for sentence in gps_sentences:
                            nmea_f.write(sentence + "\n")
                            self._add_reference_data(sentence, "GPS", sim_current_time, vessel_state.mmsi, vessel_state)
                            self._write_human_readable(human_f, sentence, "GPS", sim_current_time, vessel_state)
                
                # Generate AIS Type 1 messages every 10 seconds (for each vessel)
                if step % 10 == 0:
                    for v_gen in self.vessel_generators:
                        vessel_state = v_gen.get_current_state()
                        try:
                            # Use the AISMessageGenerator instance
                            ais_sentences, _ = self.ais_message_generator.generate_type_1(vessel_state)
                            for sentence in ais_sentences:
                                nmea_f.write(sentence + "\n")
                                self._add_reference_data(sentence, "AIS", sim_current_time, vessel_state.mmsi, vessel_state, 1)
                                self._write_human_readable(human_f, sentence, "AIS", sim_current_time, vessel_state, 1)
                        except Exception as e:
                            print(f"Error generating AIS Type 1 for vessel {vessel_state.mmsi}: {e}")
                
                # Generate AIS Type 5 messages every 30 seconds (was 60)
                if step % 30 == 0:
                    for v_gen in self.vessel_generators:
                        vessel_state = v_gen.get_current_state()
                        if vessel_state.static_data.vessel_class == VesselClass.CLASS_A: # Type 5 is for Class A
                            try:
                                ais_sentences, _ = self.ais_message_generator.generate_type_5(vessel_state)
                                for sentence in ais_sentences:
                                    nmea_f.write(sentence + "\n")
                                    self._add_reference_data(sentence, "AIS", sim_current_time, vessel_state.mmsi, vessel_state, 5)
                                    self._write_human_readable(human_f, sentence, "AIS", sim_current_time, vessel_state, 5)
                            except Exception as e:
                                print(f"Error generating AIS Type 5 for vessel {vessel_state.mmsi}: {e}")
                
                if step % 15 == 0: # Print progress more often for shorter test
                    elapsed_loop = (sim_current_time - sim_start_time).total_seconds()
                    progress = elapsed_loop / (duration_minutes * 60) * 100
                    print(f"Progress: {progress:.1f}% - Sim Time: {sim_current_time.strftime('%H:%M:%S')} - Messages: {self.message_count}")
                
                sim_current_time += timedelta(seconds=time_step_seconds)
        
        self._save_reference_data(reference_file)
        
        print(f"\nScenario generation complete!")
        print(f"Generated {self.message_count} messages")
        print(f"Files created in '{self.output_dir}':")
        print(f"  NMEA output: {nmea_file.name}")
        print(f"  Reference data: {reference_file.name}")
        print(f"  Human readable: {human_file.name}")
        
        return {
            'nmea_file': str(nmea_file),
            'reference_file': str(reference_file),
            'human_readable': str(human_file)
        }
    
    # _update_vessel_positions is removed as EnhancedVesselGenerator handles updates.
    
    def _generate_gps_sentences(self, vessel_state: VesselState, current_time: datetime):
        """Generate GPS sentences for a vessel state."""
        sentences = []
        nav = vessel_state.navigation_data
        
        nmea_time_obj = NMEATime.from_datetime(current_time)
        nmea_date_obj = NMEADate.from_date(current_time.date())
        time_str = nmea_time_obj.to_nmea()
        date_str = nmea_date_obj.to_nmea()
        
        gga_builder = SentenceBuilder(TalkerId.GP, SentenceId.GGA)
        gga_builder.add_field(time_str)

        lat_str, lat_hem, lon_str, lon_hem = nav.position.to_nmea()
        gga_builder.add_field(lat_str).add_field(lat_hem).add_field(lon_str).add_field(lon_hem)
        gga_builder.add_field(str(nav.fix_quality.value if hasattr(nav, 'fix_quality') else 1)) # Assuming fix_quality is available
        gga_builder.add_field(str(nav.satellites_in_use if hasattr(nav, 'satellites_in_use') else 8))
        gga_builder.add_float_field(nav.hdop if hasattr(nav, 'hdop') else 1.2, 1)
        gga_builder.add_float_field(nav.altitude.value if hasattr(nav, 'altitude') else 0.0, 1)
        gga_builder.add_field("M")
        gga_builder.add_float_field(nav.geoid_height.value if hasattr(nav, 'geoid_height') else 19.6, 1)
        gga_builder.add_field("M").add_field("").add_field("")
        sentences.append(gga_builder.build().strip())
        
        rmc_builder = SentenceBuilder(TalkerId.GP, SentenceId.RMC)
        rmc_builder.add_field(time_str)
        rmc_builder.add_field(nav.status.value if hasattr(nav, 'status') else "A") # DataStatus.ACTIVE
        rmc_builder.add_field(lat_str).add_field(lat_hem).add_field(lon_str).add_field(lon_hem)
        rmc_builder.add_float_field(nav.sog, 1)
        rmc_builder.add_float_field(nav.cog, 1)
        rmc_builder.add_field(date_str)
        rmc_builder.add_float_field(nav.magnetic_variation if hasattr(nav, 'magnetic_variation') else 0.0, 1)
        rmc_builder.add_field(nav.magnetic_variation_direction.value if hasattr(nav, 'magnetic_variation_direction') else "E")
        # RMC mode indicator (optional in some NMEA versions)
        # Assuming nav.mode_indicator exists, otherwise default or omit
        rmc_builder.add_field(nav.mode_indicator.value if hasattr(nav, 'mode_indicator') else "A")
        sentences.append(rmc_builder.build().strip())
        
        return sentences
    
    # _generate_ais_type1 and _generate_ais_type5 are now handled by AISMessageGenerator
    # using the dynamic vessel_state in the main loop.

    def _add_reference_data(self, sentence, msg_type, timestamp, vessel_mmsi, vessel_state: VesselState, ais_msg_type=None):
        """Add reference data for validation, using current VesselState."""
        nav = vessel_state.navigation_data
        static = vessel_state.static_data
        ref = {
            'timestamp': timestamp.isoformat(),
            'message_type': msg_type,
            'sentence': sentence,
            'vessel_mmsi': vessel_mmsi,
            'ais_message_type': ais_msg_type,
            'vessel_data': { # Capture current dynamic data
                'name': static.vessel_name,
                'position': {'latitude': nav.position.latitude, 'longitude': nav.position.longitude},
                'sog': nav.sog,
                'cog': nav.cog,
                'heading': nav.heading,
                'rot': nav.rot,
                'nav_status': nav.nav_status.name
            }
        }
        self.reference_data.append(ref)
        self.message_count += 1
    
    def _write_human_readable(self, file, sentence, msg_type, timestamp, vessel_state: VesselState, ais_msg_type=None):
        """Write human-readable explanation using current VesselState."""
        time_str = timestamp.strftime('%H:%M:%S')
        nav = vessel_state.navigation_data
        static = vessel_state.static_data
        
        file.write(f"[{time_str}] ")
        
        if msg_type == 'GPS':
            if sentence.startswith('$GPGGA'):
                file.write(f"GPS Fix - {static.vessel_name} (MMSI: {vessel_state.mmsi})\n")
                file.write(f"  Position: {nav.position.latitude:.6f}, {nav.position.longitude:.6f}, SOG: {nav.sog:.1f}kn, COG: {nav.cog:.1f}deg\n")
            elif sentence.startswith('$GPRMC'):
                file.write(f"GPS RMC - {static.vessel_name}\n")
                file.write(f"  Speed: {nav.sog:.1f} knots, Course: {nav.cog:.1f}°, Time: {time_str}\n")
        
        elif msg_type == 'AIS':
            file.write(f"AIS Type {ais_msg_type} - {static.vessel_name} (MMSI: {vessel_state.mmsi})\n")
            if ais_msg_type == 1:
                file.write(f"  Position Report: Lat={nav.position.latitude:.4f}, Lon={nav.position.longitude:.4f}\n")
                file.write(f"  SOG: {nav.sog:.1f}kn, COG: {nav.cog:.1f}°, HDG: {nav.heading}°, ROT: {nav.rot}\n")
            elif ais_msg_type == 5:
                file.write(f"  Static Data: Name={static.vessel_name}, CallSign={static.callsign}\n")
        
        file.write(f"  Sentence: {sentence}\n\n")
    
    def _save_reference_data(self, file_path):
        """Save reference data to JSON file."""
        # Simplified vessels part for this refactor
        vessel_gens_info = []
        for v_gen in self.vessel_generators:
            vs = v_gen.get_current_state() # Get the final state for this summary
            vessel_gens_info.append({
                'mmsi': vs.mmsi,
                'name': vs.static_data.vessel_name,
                'call_sign': vs.static_data.callsign,
                'ship_type': vs.static_data.ship_type.value,
                'vessel_class': vs.static_data.vessel_class.value
            })

        data = {
            'generation_info': {
                'timestamp': datetime.utcnow().isoformat(),
                'vessel_count': len(self.vessel_generators),
                'total_messages': len(self.reference_data)
            },
            'vessels_initial_config_summary': vessel_gens_info, # Summary of what was simulated
            'messages': self.reference_data
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)


def main():
    """Main function."""
    print("=" * 60)
    print("SIMPLE NMEA+AIS SIMULATOR (DYNAMIC AIS)")
    print("=" * 60)
    
    # Use default values directly for non-interactive testing
    duration = 0.4  # e.g., 24 seconds for a quick test, to get at least two Type 1 AIS
    output_dir = "simple_output_dynamic_test"
    print(f"Using default duration: {duration} minutes")
    print(f"Using default output directory: {output_dir}")

    # try:
    #     duration_input = input("Duration in minutes (e.g., 1 for 1 min) [1]: ").strip()
    #     duration = int(duration_input) if duration_input else 1
        
    #     output_dir_input = input("Output directory [simple_output_dynamic]: ").strip()
    #     output_dir = output_dir_input if output_dir_input else "simple_output_dynamic"
        
    # except (ValueError, KeyboardInterrupt):
    #     print("Invalid input or interrupted. Using default values...")
    #     duration = 1
    #     output_dir = "simple_output_dynamic"
    
    print(f"\nGenerating {duration}-minute scenario in '{output_dir}'...")
    
    simulator = SimpleNMEASimulator(output_dir)
    files = simulator.generate_scenario(duration)
    
    print("\n" + "=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    
    nmea_file = files['nmea_file']
    if Path(nmea_file).exists():
        print("\nSample NMEA output (first 20 lines if available):")
        with open(nmea_file, 'r') as f:
            for i, line in enumerate(f):
                if i >= 20:
                    break
                print(f"  {line.strip()}")
    
    print(f"\nReference data JSON: {files['reference_file']}")
    print(f"Human readable log: {files['human_readable']}")


if __name__ == "__main__":
    main()
