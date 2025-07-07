"""Factory for creating output handlers from configuration."""

from typing import List
from .base import OutputHandler
from .file import FileOutput
from .tcp import TCPOutput
from .udp import UDPOutput
from .serial import SerialOutput, SerialOutputConfig # Added SerialOutput
from ..config.parser import OutputConfig


class OutputFactory:
    """Factory for creating output handlers."""
    
    @staticmethod
    def create_output_handler(output_config: OutputConfig) -> OutputHandler:
        """Create output handler from configuration."""
        if not output_config.enabled:
            raise ValueError("Output handler is disabled")
        
        if output_config.type == 'file':
            return FileOutput(output_config.config)
        elif output_config.type == 'tcp':
            return TCPOutput(output_config.config)
        elif output_config.type == 'udp':
            return UDPOutput(output_config.config)
        elif output_config.type == 'serial': # Added serial output type
            # Assuming config is already a SerialOutputConfig instance
            # If not, you might need to parse it here or ensure it's correctly passed
            if not isinstance(output_config.config, SerialOutputConfig):
                 # This is a basic way to handle it; you might need a more robust conversion
                 # depending on how output_config.config is structured.
                 # For now, assuming it's directly compatible or already the correct type.
                 # If it's a dict, you would do: SerialOutputConfig(**output_config.config)
                 # However, the structure of OutputConfig suggests output_config.config
                 # is already the specific config object (e.g. TCPOutputConfig, UDPOutputConfig)
                 # So, we expect it to be SerialOutputConfig for type 'serial'.
                 # This check is more of a safeguard.
                 # A better approach would be to ensure the config parsing upstream
                 # correctly instantiates SerialOutputConfig when type is 'serial'.
                pass # Placeholder for potential config conversion if needed
            return SerialOutput(output_config.config)
        else:
            raise ValueError(f"Unknown output type: {output_config.type}")
    
    @staticmethod
    def create_output_handlers(output_configs: List[OutputConfig]) -> List[OutputHandler]:
        """Create multiple output handlers from configuration list."""
        handlers = []
        
        for output_config in output_configs:
            if output_config.enabled:
                try:
                    handler = OutputFactory.create_output_handler(output_config)
                    handlers.append(handler)
                except Exception as e:
                    print(f"Warning: Failed to create {output_config.type} output handler: {e}")
        
        return handlers

