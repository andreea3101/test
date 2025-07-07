"""AIVDM sentence generation for AIS messages."""

from typing import List, Tuple, Dict, Any, Optional
from nmea_lib.ais.encoder import AIS6BitEncoder, AISMultiPartHandler
from nmea_lib.ais.messages import AISBinaryEncoder
from nmea_lib.ais.constants import AIS_CHANNELS
from nmea_lib.types.vessel import VesselState, BaseStationData, AidToNavigationData


class AIVDMSentence:
    """AIVDM sentence for AIS message transmission."""
    
    def __init__(self, total_sentences: int = 1, sentence_number: int = 1,
                 sequential_message_id: Optional[str] = None, channel: str = 'A',
                 payload: str = '', fill_bits: int = 0):
        """Initialize AIVDM sentence."""
        self.total_sentences = total_sentences
        self.sentence_number = sentence_number
        self.sequential_message_id = sequential_message_id or ""
        self.channel = channel
        self.payload = payload
        self.fill_bits = fill_bits
    
    def __str__(self) -> str:
        """Convert to NMEA sentence string."""
        # Build sentence fields
        fields = [
            "AIVDM",
            str(self.total_sentences),
            str(self.sentence_number),
            self.sequential_message_id,
            self.channel,
            self.payload,
            str(self.fill_bits)
        ]
        
        # Create sentence body
        sentence_body = ",".join(fields)
        
        # Calculate checksum
        checksum = 0
        for char in sentence_body:
            checksum ^= ord(char)
        
        # Return complete sentence
        return f"!{sentence_body}*{checksum:02X}"
    
    @classmethod
    def from_binary_message(cls, binary_data: str, channel: str = 'A',
                          sequential_id: Optional[str] = None) -> List['AIVDMSentence']:
        """Create AIVDM sentence(s) from binary AIS message."""
        sentences = []
        
        # Check if message needs splitting
        if AISMultiPartHandler.needs_splitting(binary_data):
            # Split into multiple parts
            parts = AISMultiPartHandler.split_message(binary_data)
            total_parts = len(parts)
            
            for i, part in enumerate(parts):
                # Calculate fill bits for this part
                fill_bits = AIS6BitEncoder.calculate_fill_bits(len(part))
                
                # Encode to 6-bit ASCII
                encoded_payload = AIS6BitEncoder.encode_binary_to_6bit(part)
                
                # Create sentence
                sentence = cls(
                    total_sentences=total_parts,
                    sentence_number=i + 1,
                    sequential_message_id=sequential_id,
                    channel=channel,
                    payload=encoded_payload,
                    fill_bits=fill_bits
                )
                sentences.append(sentence)
        else:
            # Single sentence
            fill_bits = AIS6BitEncoder.calculate_fill_bits(len(binary_data))
            encoded_payload = AIS6BitEncoder.encode_binary_to_6bit(binary_data)
            
            sentence = cls(
                total_sentences=1,
                sentence_number=1,
                sequential_message_id=sequential_id,
                channel=channel,
                payload=encoded_payload,
                fill_bits=fill_bits
            )
            sentences.append(sentence)
        
        return sentences
    
    def get_message_type(self) -> Optional[int]:
        """Extract AIS message type from payload."""
        if not self.payload:
            return None
        
        try:
            # Decode first 6 bits to get message type
            binary = AIS6BitEncoder.decode_6bit_to_binary(self.payload[:1])
            if len(binary) >= 6:
                return int(binary[:6], 2)
        except (ValueError, IndexError):
            pass
        
        return None
    
    def validate(self) -> bool:
        """Validate AIVDM sentence format."""
        # Check AIVDM-specific fields
        if not (1 <= self.total_sentences <= 9):
            return False
        
        if not (1 <= self.sentence_number <= self.total_sentences):
            return False
        
        if self.channel not in AIS_CHANNELS:
            return False
        
        if not (0 <= self.fill_bits <= 5):
            return False
        
        # Validate payload is valid 6-bit ASCII
        if not AIS6BitEncoder.validate_6bit_string(self.payload):
            return False
        
        return True


class AISMessageGenerator:
    """Generates AIVDM sentences from vessel data."""
    
    def __init__(self):
        """Initialize AIS message generator."""
        self.sequence_counter = 0
    
    def _get_next_sequence_id(self) -> str:
        """Get next sequential message ID for multi-part messages."""
        self.sequence_counter = (self.sequence_counter + 1) % 10
        return str(self.sequence_counter) if self.sequence_counter > 0 else ""
    
    def generate_type_1(self, vessel: VesselState, channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 1 Position Report."""
        binary_data, input_data = AISBinaryEncoder.encode_type_1(vessel)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_2(self, vessel: VesselState, channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 2 Position Report (Scheduled)."""
        binary_data, input_data = AISBinaryEncoder.encode_type_2(vessel)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_3(self, vessel: VesselState, channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 3 Position Report (Response)."""
        binary_data, input_data = AISBinaryEncoder.encode_type_3(vessel)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_4(self, base_station: BaseStationData, channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 4 Base Station Report."""
        binary_data, input_data = AISBinaryEncoder.encode_type_4(base_station)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_5(self, vessel: VesselState, channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 5 Static and Voyage Data."""
        binary_data, input_data = AISBinaryEncoder.encode_type_5(vessel)
        seq_id = self._get_next_sequence_id()
        sentences = AIVDMSentence.from_binary_message(binary_data, channel, seq_id)
        return [str(s) for s in sentences], input_data
    
    def generate_type_18(self, vessel: VesselState, channel: str = 'B') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 18 Class B Position Report."""
        binary_data, input_data = AISBinaryEncoder.encode_type_18(vessel)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_19(self, vessel: VesselState, channel: str = 'B') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 19 Extended Class B Report."""
        binary_data, input_data = AISBinaryEncoder.encode_type_19(vessel)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_21(self, aid_nav: AidToNavigationData, channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 21 Aid-to-Navigation Report."""
        binary_data, input_data = AISBinaryEncoder.encode_type_21(aid_nav)
        sentences = AIVDMSentence.from_binary_message(binary_data, channel)
        return [str(s) for s in sentences], input_data
    
    def generate_type_24(self, vessel: VesselState, channel: str = 'B') -> Tuple[List[str], Dict[str, Any]]:
        """Generate Type 24 Static Data Report (both parts)."""
        # Generate Part A
        binary_a, input_a = AISBinaryEncoder.encode_type_24_part_a(vessel)
        sentences_a = AIVDMSentence.from_binary_message(binary_a, channel)
        
        # Generate Part B
        binary_b, input_b = AISBinaryEncoder.encode_type_24_part_b(vessel)
        sentences_b = AIVDMSentence.from_binary_message(binary_b, channel)
        
        # Combine sentences
        all_sentences = [str(s) for s in sentences_a] + [str(s) for s in sentences_b]
        
        # Combine input data
        combined_input = {
            'part_a': input_a,
            'part_b': input_b
        }
        
        return all_sentences, combined_input
    
    def generate_message(self, message_type: int, vessel_data: Any, 
                        channel: str = 'A') -> Tuple[List[str], Dict[str, Any]]:
        """Generate AIS message of specified type."""
        generators = {
            1: self.generate_type_1,
            2: self.generate_type_2,
            3: self.generate_type_3,
            4: self.generate_type_4,
            5: self.generate_type_5,
            18: self.generate_type_18,
            19: self.generate_type_19,
            21: self.generate_type_21,
            24: self.generate_type_24,
        }
        
        if message_type not in generators:
            raise ValueError(f"Unsupported AIS message type: {message_type}")

        # Prepare appropriate data object based on message type
        actual_data = vessel_data
        if message_type == 4:
            if isinstance(vessel_data, VesselState):
                # Create BaseStationData from VesselState
                actual_data = BaseStationData(
                    mmsi=vessel_data.mmsi,
                    position=vessel_data.navigation_data.position,
                    timestamp=vessel_data.timestamp_sim, # or datetime.now()
                    epfd_type=vessel_data.static_data.epfd_type,
                    # raim and radio_status can be defaulted or taken from vessel_data if available/applicable
                    raim=getattr(vessel_data.navigation_data, 'raim', 0),
                    radio_status=getattr(vessel_data.navigation_data, 'radio_status', 0)
                )
            elif not isinstance(vessel_data, BaseStationData):
                raise TypeError(f"AIS Type 4 requires BaseStationData, got {type(vessel_data)}")
        
        elif message_type == 21:
            if isinstance(vessel_data, VesselState):
                # Attempt to create AidToNavigationData from VesselState
                # This is a simplification; real AtoN would have specific AtoN data
                actual_data = AidToNavigationData(
                    mmsi=vessel_data.mmsi,
                    name=vessel_data.static_data.vessel_name[:20] if vessel_data.static_data.vessel_name else "AtoN",
                    position=vessel_data.navigation_data.position,
                    aid_type=getattr(vessel_data.static_data, 'aid_type', 0), # Default if not present
                    dimensions=vessel_data.static_data.dimensions,
                    epfd_type=vessel_data.static_data.epfd_type,
                    timestamp=vessel_data.navigation_data.timestamp,
                    # Other fields can be defaulted
                    off_position=0,
                    regional=0,
                    raim=getattr(vessel_data.navigation_data, 'raim', 0),
                    virtual_aid=0,
                    assigned=0,
                    position_accuracy=getattr(vessel_data.navigation_data, 'position_accuracy', 0)
                )
            elif not isinstance(vessel_data, AidToNavigationData):
                raise TypeError(f"AIS Type 21 requires AidToNavigationData, got {type(vessel_data)}")

        return generators[message_type](actual_data, channel)


# Utility functions for testing and validation
def validate_aivdm_sentence(sentence: str) -> bool:
    """Validate an AIVDM sentence string."""
    try:
        # Parse sentence
        if not sentence.startswith('!AIVDM,'):
            return False
        
        # Basic format check
        if '*' not in sentence:
            return False
        
        # Parse fields
        parts = sentence.split(',')
        if len(parts) < 7:
            return False
        
        # Validate AIVDM-specific fields
        total_sentences = int(parts[1])
        sentence_number = int(parts[2])
        channel = parts[4]
        payload = parts[5]
        fill_bits = int(parts[6].split('*')[0])
        
        # Create AIVDM object for validation
        aivdm = AIVDMSentence(total_sentences, sentence_number, parts[3], 
                             channel, payload, fill_bits)
        return aivdm.validate()
        
    except (ValueError, IndexError):
        return False


def decode_aivdm_payload(payload: str, fill_bits: int = 0) -> str:
    """Decode AIVDM payload to binary string."""
    binary = AIS6BitEncoder.decode_6bit_to_binary(payload)
    
    # Remove fill bits from the end
    if fill_bits > 0:
        binary = binary[:-fill_bits]
    
    return binary


def extract_message_type(sentence: str) -> Optional[int]:
    """Extract AIS message type from AIVDM sentence."""
    try:
        parts = sentence.split(',')
        if len(parts) >= 6 and parts[0] == '!AIVDM':
            payload = parts[5]
            if payload:
                # Decode first character to get message type
                binary = AIS6BitEncoder.decode_6bit_to_binary(payload[0])
                if len(binary) >= 6:
                    return int(binary[:6], 2)
    except (ValueError, IndexError):
        pass
    
    return None

