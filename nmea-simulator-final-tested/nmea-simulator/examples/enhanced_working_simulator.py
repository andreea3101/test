#!/usr/bin/env python3
"""
Enhanced Working NMEA+AIS Simulator - Refactored for Dynamic AIS

This example demonstrates the complete NMEA simulator with:
1. Dynamic AIS message generation
2. TCP/UDP network output support
3. Complete scenario generation with reference data
4. Human-readable output for debugging
"""

import sys
import os
import json
import time
import socket
import threading
from datetime import datetime, timedelta
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nmea_lib.types import Position
from nmea_lib.sentences.aivdm import AISMessageGenerator
from nmea_lib.types.datetime import NMEATime, NMEADate
from nmea_lib.types.vessel import VesselState, VesselClass, ShipType, NavigationStatus

from simulator.generators.vessel import EnhancedVesselGenerator, create_default_vessel_config
from nmea_lib.parser import SentenceBuilder
from nmea_lib.base import TalkerId, SentenceId


class NetworkOutput:
    """Handle TCP and UDP network output."""
    
    def __init__(self, tcp_port=None, udp_port=None, udp_host="255.255.255.255"):
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.udp_host = udp_host
        self.tcp_server = None
        self.udp_socket = None
        self.tcp_clients = []
        self.running = False
        if tcp_port: self._setup_tcp_server()
        if udp_port: self._setup_udp_socket()
    
    def _setup_tcp_server(self):
        try:
            self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_server.bind(('0.0.0.0', self.tcp_port))
            self.tcp_server.listen(5)
            self.tcp_server.settimeout(1.0)
            self.running = True
            threading.Thread(target=self._tcp_server_loop, daemon=True).start()
            print(f"TCP server listening on port {self.tcp_port}")
        except Exception as e:
            print(f"Failed to setup TCP server: {e}")
            self.tcp_server = None
    
    def _setup_udp_socket(self):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            print(f"UDP broadcast setup on port {self.udp_port}")
        except Exception as e:
            print(f"Failed to setup UDP socket: {e}")
            self.udp_socket = None
    
    def _tcp_server_loop(self):
        while self.running and self.tcp_server:
            try:
                client_socket, address = self.tcp_server.accept()
                self.tcp_clients.append(client_socket)
                print(f"TCP client connected from {address}")
            except socket.timeout: continue
            except Exception as e:
                if self.running: print(f"TCP server error: {e}")
                break
    
    def send_sentence(self, sentence):
        sentence_with_newline = sentence + "\n"
        if self.tcp_clients:
            disconnected_clients = []
            for client in self.tcp_clients:
                try: client.send(sentence_with_newline.encode('utf-8'))
                except: disconnected_clients.append(client)
            for client in disconnected_clients:
                self.tcp_clients.remove(client)
                try: client.close()
                except: pass
        if self.udp_socket and self.udp_port:
            try:
                self.udp_socket.sendto(sentence_with_newline.encode('utf-8'), (self.udp_host, self.udp_port))
            except Exception as e: print(f"UDP send error: {e}")
    
    def close(self):
        self.running = False
        if self.tcp_server: self.tcp_server.close()
        for client in self.tcp_clients:
            try: client.close()
            except: pass
        if self.udp_socket: self.udp_socket.close()


class EnhancedNMEASimulator:
    """Enhanced NMEA simulator with dynamic AIS and network support."""
    
    def __init__(self, output_dir="enhanced_output_dynamic", tcp_port=None, udp_port=None):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.vessel_generators: list[EnhancedVesselGenerator] = [] # Store generators
        self.reference_data = []
        self.message_count = 0
        
        self.network = NetworkOutput(tcp_port, udp_port)
        self.ais_message_generator = AISMessageGenerator()
        
        self._create_dynamic_vessels()
    
    def _create_dynamic_vessels(self):
        """Create dynamic vessel generators."""
        vessel_configs = [
            create_default_vessel_config(mmsi=367001234, name="DYNAMIC EVER", position=Position(37.8000, -122.4000), vessel_class='A'),
            create_default_vessel_config(mmsi=367002345, name="DYNAMIC PACIFIC", position=Position(37.7500, -122.4500), vessel_class='A')
        ]

        # Customize vessel1 (Container Ship)
        vessel_configs[0].update({
            'initial_speed': 15.5, 'initial_heading': 90.0,
            'callsign': "TEST123", 'ship_type': ShipType.CARGO_ALL_SHIPS,
            'dimensions': {'to_bow': 150, 'to_stern': 50, 'to_port': 15, 'to_starboard': 15},
            'voyage': {'destination': "OAKLAND", 'draught': 12.5}
        })

        # Customize vessel2 (Fishing Vessel)
        vessel_configs[1].update({
            'initial_speed': 8.2, 'initial_heading': 180.0,
            'callsign': "FISH01", 'ship_type': ShipType.FISHING, 'nav_status': NavigationStatus.ENGAGED_IN_FISHING,
            'dimensions': {'to_bow': 25, 'to_stern': 5, 'to_port': 4, 'to_starboard': 4}
        })

        for config in vessel_configs:
            self.vessel_generators.append(EnhancedVesselGenerator(config))

    def generate_scenario(self, duration_minutes=1): # Shortened for testing
        print(f"Generating {duration_minutes}-minute scenario with {len(self.vessel_generators)} dynamic vessels...")
        
        nmea_file = self.output_dir / "nmea_output_dynamic.txt"
        reference_file = self.output_dir / "reference_data_dynamic.json"
        human_file = self.output_dir / "human_readable_dynamic.txt"
        
        sim_current_time = datetime.utcnow()
        sim_start_time = sim_current_time
        sim_end_time = sim_start_time + timedelta(minutes=duration_minutes)
        
        with open(nmea_file, 'w') as nmea_f, open(human_file, 'w') as human_f:
            human_f.write("Dynamic NMEA Simulator Output - Human Readable\n" + "="*60 + "\n" +
                          f"Generated: {sim_start_time.strftime('%Y-%m-%d %H:%M:%S UTC')}\n" +
                          f"Duration: {duration_minutes} minutes\n" +
                          f"Vessels: {len(self.vessel_generators)}\n" + "="*60 + "\n\n")
            
            step = 0
            time_step_seconds = 1.0

            while sim_current_time < sim_end_time:
                step += 1
                
                for v_gen in self.vessel_generators:
                    v_gen.update_vessel_state(elapsed_seconds=time_step_seconds, current_time=sim_current_time)
                
                if step % 5 == 0: # GPS every 5s
                    for v_gen in self.vessel_generators:
                        v_state = v_gen.get_current_state()
                        gps_sentences = self._generate_gps_sentences(v_state, sim_current_time)
                        for sentence in gps_sentences:
                            nmea_f.write(sentence + "\n"); self.network.send_sentence(sentence)
                            self._add_reference_data(sentence, "GPS", sim_current_time, v_state, None)
                            self._write_human_readable(human_f, sentence, "GPS", sim_current_time, v_state)
                
                if step % 10 == 0: # AIS Type 1 every 10s
                    for v_gen in self.vessel_generators:
                        v_state = v_gen.get_current_state()
                        try:
                            ais_sentences, _ = self.ais_message_generator.generate_type_1(v_state)
                            for sentence in ais_sentences:
                                nmea_f.write(sentence + "\n"); self.network.send_sentence(sentence)
                                self._add_reference_data(sentence, "AIS", sim_current_time, v_state, 1)
                                self._write_human_readable(human_f, sentence, "AIS", sim_current_time, v_state, 1)
                        except Exception as e: print(f"Error AIS Type 1 for {v_state.mmsi}: {e}")
                
                if step % 30 == 0: # AIS Type 5 every 30s (was 60)
                    for v_gen in self.vessel_generators:
                        v_state = v_gen.get_current_state()
                        if v_state.static_data.vessel_class == VesselClass.CLASS_A:
                            try:
                                ais_sentences, _ = self.ais_message_generator.generate_type_5(v_state)
                                for sentence in ais_sentences:
                                    nmea_f.write(sentence + "\n"); self.network.send_sentence(sentence)
                                    self._add_reference_data(sentence, "AIS", sim_current_time, v_state, 5)
                                    self._write_human_readable(human_f, sentence, "AIS", sim_current_time, v_state, 5)
                            except Exception as e: print(f"Error AIS Type 5 for {v_state.mmsi}: {e}")
                
                if step % 15 == 0:
                    elapsed_loop = (sim_current_time - sim_start_time).total_seconds()
                    progress = elapsed_loop / (duration_minutes * 60) * 100
                    tcp_clients = len(self.network.tcp_clients)
                    print(f"Progress: {progress:.1f}% - SimTime: {sim_current_time.strftime('%H:%M:%S')} - Msgs: {self.message_count} - TCP Clients: {tcp_clients}")
                
                sim_current_time += timedelta(seconds=time_step_seconds)
        
        self._save_reference_data(reference_file)
        print(f"\nScenario generation complete! Generated {self.message_count} messages.")
        # ... (rest of file printing)
        return {'nmea_file': str(nmea_file), 'reference_file': str(reference_file), 'human_readable': str(human_file)}

    def _generate_gps_sentences(self, vessel_state: VesselState, current_time: datetime):
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
        gga_builder.add_field(str(nav.fix_quality.value if hasattr(nav, 'fix_quality') and nav.fix_quality else 1))
        gga_builder.add_field(str(nav.satellites_in_use if hasattr(nav, 'satellites_in_use') else 8))
        gga_builder.add_float_field(nav.hdop if hasattr(nav, 'hdop') else 1.2, 1)
        gga_builder.add_float_field(nav.altitude.value if hasattr(nav, 'altitude') and nav.altitude else 0.0, 1)
        gga_builder.add_field("M")
        gga_builder.add_float_field(nav.geoid_height.value if hasattr(nav, 'geoid_height') and nav.geoid_height else 19.6, 1)
        gga_builder.add_field("M").add_field("").add_field("")
        sentences.append(gga_builder.build().strip())
        
        rmc_builder = SentenceBuilder(TalkerId.GP, SentenceId.RMC)
        rmc_builder.add_field(time_str)
        rmc_builder.add_field(nav.status.value if hasattr(nav, 'status') and nav.status else "A")
        rmc_builder.add_field(lat_str).add_field(lat_hem).add_field(lon_str).add_field(lon_hem)
        rmc_builder.add_float_field(nav.sog, 1)
        rmc_builder.add_float_field(nav.cog, 1)
        rmc_builder.add_field(date_str)
        rmc_builder.add_float_field(nav.magnetic_variation if hasattr(nav, 'magnetic_variation') else 0.0, 1)
        rmc_builder.add_field(nav.magnetic_variation_direction.value if hasattr(nav, 'magnetic_variation_direction') and nav.magnetic_variation_direction else "E")
        rmc_builder.add_field(nav.mode_indicator.value if hasattr(nav, 'mode_indicator') and nav.mode_indicator else "A")
        sentences.append(rmc_builder.build().strip())
        return sentences

    def _add_reference_data(self, sentence, msg_type, timestamp, vessel_state: VesselState, ais_msg_type=None):
        nav = vessel_state.navigation_data
        static = vessel_state.static_data
        ref = {
            'timestamp': timestamp.isoformat(), 'message_type': msg_type, 'sentence': sentence,
            'vessel_mmsi': vessel_state.mmsi, 'ais_message_type': ais_msg_type,
            'vessel_data': {
                'name': static.vessel_name,
                'position': {'latitude': nav.position.latitude, 'longitude': nav.position.longitude},
                'sog': nav.sog, 'cog': nav.cog, 'heading': nav.heading, 'rot': nav.rot,
                'nav_status': nav.nav_status.name
            }}
        self.reference_data.append(ref)
        self.message_count += 1

    def _write_human_readable(self, file, sentence, msg_type, timestamp, v_state: VesselState, ais_msg_type=None):
        time_str = timestamp.strftime('%H:%M:%S')
        nav = v_state.navigation_data; static = v_state.static_data
        file.write(f"[{time_str}] ")
        if msg_type == 'GPS':
            file.write(f"GPS ({static.vessel_name} MMSI: {v_state.mmsi}) {sentence.split(',')[0]}: " +
                       f"Pos={nav.position.latitude:.4f},{nav.position.longitude:.4f} SOG={nav.sog:.1f} COG={nav.cog:.1f}\n")
        elif msg_type == 'AIS':
            file.write(f"AIS Type {ais_msg_type} ({static.vessel_name} MMSI: {v_state.mmsi}): " +
                       f"Pos={nav.position.latitude:.4f},{nav.position.longitude:.4f} SOG={nav.sog:.1f} COG={nav.cog:.1f} HDG={nav.heading}\n")
        file.write(f"  Sentence: {sentence}\n\n")

    def _save_reference_data(self, file_path):
        v_gens_info = [{'mmsi': vg.get_current_state().mmsi, 'name': vg.get_current_state().static_data.vessel_name} for vg in self.vessel_generators]
        data = {'generation_info': {'timestamp': datetime.utcnow().isoformat(), 'vessel_count': len(self.vessel_generators), 'total_messages': self.message_count},
                'vessels_initial_config_summary': v_gens_info, 'messages': self.reference_data}
        with open(file_path, 'w') as f: json.dump(data, f, indent=2)

    def close(self): self.network.close()

def main():
    print("="*70 + "\nENHANCED NMEA+AIS SIMULATOR (DYNAMIC AIS)\n" + "="*70 + "\n")
    duration = 0.4 # Default 0.4 min (24s) for non-interactive test
    output_dir = "enhanced_output_dynamic_test"
    tcp_port, udp_port = 2000, 2001 # Defaults for testing

    if sys.stdin.isatty(): # If running interactively, allow input
        try:
            duration_input = input(f"Duration in minutes [{duration}]: ").strip()
            duration = float(duration_input) if duration_input else duration
            output_dir_input = input(f"Output directory [{output_dir}]: ").strip()
            output_dir = output_dir_input if output_dir_input else output_dir
            tcp_input = input(f"TCP port (empty to disable) [{tcp_port}]: ").strip()
            tcp_port = int(tcp_input) if tcp_input else None
            udp_input = input(f"UDP port (empty to disable) [{udp_port}]: ").strip()
            udp_port = int(udp_input) if udp_input else None
        except (ValueError, KeyboardInterrupt): print("Using default/previous values...")
    
    print(f"\nConfig: Duration={duration}m, Output='{output_dir}', TCP={tcp_port}, UDP={udp_port}\n")
    
    simulator = EnhancedNMEASimulator(output_dir, tcp_port, udp_port)
    try:
        if tcp_port or udp_port:
            print("Starting simulation & network servers... Press Ctrl+C to stop early.")
            print(f"  TCP: localhost:{tcp_port}" if tcp_port else "  TCP: disabled")
            print(f"  UDP: broadcast port {udp_port}" if udp_port else "  UDP: disabled")
        else:
            print("Starting simulation (network output disabled)...")

        files = simulator.generate_scenario(duration)
        print("\n" + "="*70 + "\nGENERATION COMPLETE\n" + "="*70)
        # ... (sample output printing) ...
        if tcp_port or udp_port:
            print("\nNetwork servers still running. Press Enter or Ctrl+C to stop them...")
            if sys.stdin.isatty(): input()
            else: time.sleep(5) # Keep alive for a bit in non-interactive if network was on
    except KeyboardInterrupt: print("\nStopping simulation...")
    finally:
        simulator.close()
        print("Network connections closed (if any). Simulator finished.")

if __name__ == "__main__":
    main()
