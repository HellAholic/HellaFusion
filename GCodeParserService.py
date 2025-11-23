"""Service for parsing G-code files and extracting parameter values.

This service provides utility methods for:
- Reading G-code files
- Extracting parameter values from G-code lines
"""

import re
from UM.Logger import Logger


class GCodeParserService:
    """Handles G-code file reading and parameter extraction."""
    
    def readGcodeFile(self, file_path: str) -> list:
        """Read a gcode file and return lines as a list.
        
        Args:
            file_path: Path to the G-code file
            
        Returns:
            List of lines from the file, or empty list on error
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return lines
        except Exception as e:
            Logger.log("e", f"Error reading gcode file {file_path}: {str(e)}")
            return []
    
    def getValue(self, line: str, key: str) -> float:
        """Extract a numeric value for a given key from a gcode line.
        
        Args:
            line: G-code line to parse
            key: Parameter key to extract (e.g., 'X', 'Y', 'Z', 'E', 'F')
            
        Returns:
            Extracted float value, or None if not found
            
        Example:
            getValue("G1 X10.5 Y20.3 E0.5", "X") -> 10.5
            getValue("G1 Z0.2 F3000", "F") -> 3000.0
        """
        try:
            # Handle comments
            if ';' in line:
                line = line.split(';')[0]
            
            # Look for the key followed by a number
            pattern = f"{key}(-?\\d+\\.?\\d*)"
            match = re.search(pattern, line)
            if match:
                return float(match.group(1))
            return None
        except:
            return None
