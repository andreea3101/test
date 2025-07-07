"""Base classes and interfaces for NMEA sentence handling."""

from abc import ABC, abstractmethod
from typing import List, Optional, Union, Any
from dataclasses import dataclass
from enum import Enum


class TalkerId(Enum):
    """NMEA Talker ID enumeration."""
    GP = "GP"  # Global Positioning System (GPS)
    GL = "GL"  # GLONASS
    GA = "GA"  # Galileo
    GN = "GN"  # Global Navigation Satellite System (GNSS)
    BD = "BD"  # BeiDou
    QZ = "QZ"  # QZSS
    II = "II"  # Integrated Instrumentation
    IN = "IN"  # Integrated Navigation
    EC = "EC"  # Electronic Chart Display & Information System (ECDIS)
    
    @classmethod
    def parse(cls, nmea_sentence: str) -> 'TalkerId':
        """Parse talker ID from NMEA sentence."""
        if len(nmea_sentence) < 3:
            raise ValueError("Invalid NMEA sentence format")
        
        talker_str = nmea_sentence[1:3]
        try:
            return cls(talker_str)
        except ValueError:
            # Return GP as default for unknown talker IDs
            return cls.GP


class SentenceId(Enum):
    """NMEA Sentence ID enumeration."""
    GGA = "GGA"  # Global Positioning System Fix Data
    RMC = "RMC"  # Recommended Minimum Navigation Information
    GSA = "GSA"  # GPS DOP and Active Satellites
    GSV = "GSV"  # GPS Satellites in View
    VTG = "VTG"  # Track Made Good and Ground Speed
    GLL = "GLL"  # Geographic Position - Latitude/Longitude
    ZDA = "ZDA"  # Time and Date
    HDG = "HDG"  # Heading - Deviation & Variation
    
    @classmethod
    def parse(cls, nmea_sentence: str) -> 'SentenceId':
        """Parse sentence ID from NMEA sentence."""
        if len(nmea_sentence) < 6:
            raise ValueError("Invalid NMEA sentence format")
            
        sentence_str = nmea_sentence[3:6]
        try:
            return cls(sentence_str)
        except ValueError:
            raise ValueError(f"Unsupported sentence type: {sentence_str}")


class GpsFixQuality(Enum):
    """GPS Fix Quality enumeration."""
    INVALID = 0
    GPS = 1
    DGPS = 2
    PPS = 3
    RTK = 4
    FLOAT_RTK = 5
    ESTIMATED = 6
    MANUAL = 7
    SIMULATION = 8


class GpsFixStatus(Enum):
    """GPS Fix Status enumeration."""
    ACTIVE = "A"
    VOID = "V"


class Sentence(ABC):
    """Abstract base class for all NMEA sentences."""
    
    FIELD_DELIMITER = ','
    CHECKSUM_DELIMITER = '*'
    BEGIN_CHAR = '$'
    END_CHARS = '\r\n'
    
    def __init__(self, talker_id: TalkerId, sentence_id: SentenceId):
        self.talker_id = talker_id
        self.sentence_id = sentence_id
        self.fields: List[str] = []
    
    @abstractmethod
    def to_sentence(self) -> str:
        """Convert sentence object to NMEA string format."""
        pass
    
    @classmethod
    @abstractmethod
    def from_sentence(cls, nmea_sentence: str) -> 'Sentence':
        """Parse NMEA string to create sentence object."""
        pass
    
    def get_sentence_header(self) -> str:
        """Get the sentence header (e.g., '$GPGGA')."""
        return f"{self.BEGIN_CHAR}{self.talker_id.value}{self.sentence_id.value}"
    
    def calculate_checksum(self, sentence_body: str) -> str:
        """Calculate NMEA checksum for sentence body."""
        checksum = 0
        for char in sentence_body:
            checksum ^= ord(char)
        return f"{checksum:02X}"
    
    def validate_checksum(self, nmea_sentence: str) -> bool:
        """Validate NMEA sentence checksum."""
        if self.CHECKSUM_DELIMITER not in nmea_sentence:
            return False
            
        sentence_body, checksum_part = nmea_sentence.split(self.CHECKSUM_DELIMITER)
        sentence_body = sentence_body[1:]  # Remove '$' character
        
        expected_checksum = checksum_part.rstrip(self.END_CHARS)
        calculated_checksum = self.calculate_checksum(sentence_body)
        
        return expected_checksum.upper() == calculated_checksum.upper()


class PositionSentence(Sentence):
    """Base class for sentences containing position information."""
    
    @abstractmethod
    def get_latitude(self) -> Optional[float]:
        """Get latitude in decimal degrees."""
        pass
    
    @abstractmethod
    def get_longitude(self) -> Optional[float]:
        """Get longitude in decimal degrees."""
        pass
    
    @abstractmethod
    def set_position(self, latitude: float, longitude: float) -> None:
        """Set position coordinates."""
        pass


class TimeSentence(Sentence):
    """Base class for sentences containing time information."""
    
    @abstractmethod
    def get_time(self) -> Optional[str]:
        """Get time in HHMMSS.SSS format."""
        pass
    
    @abstractmethod
    def set_time(self, time_str: str) -> None:
        """Set time in HHMMSS.SSS format."""
        pass


class DateSentence(Sentence):
    """Base class for sentences containing date information."""
    
    @abstractmethod
    def get_date(self) -> Optional[str]:
        """Get date in DDMMYY format."""
        pass
    
    @abstractmethod
    def set_date(self, date_str: str) -> None:
        """Set date in DDMMYY format."""
        pass


@dataclass
class ParsedSentence:
    """Container for parsed sentence data."""
    talker_id: TalkerId
    sentence_id: SentenceId
    fields: List[str]
    checksum: str
    raw_sentence: str
    
    def is_valid(self) -> bool:
        """Check if parsed sentence is valid."""
        return len(self.fields) > 0 and len(self.checksum) == 2

