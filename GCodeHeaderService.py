"""Service for updating G-code header metadata.

This service handles updating header values after fusion, particularly:
- TIME: or PRINT.TIME: values to match final TIME_ELAPSED
"""

from UM.Logger import Logger


class GCodeHeaderService:
    """Handles updating G-code header metadata after fusion."""
    
    def updateHeaderTime(self, combined: list) -> list:
        """Update ;TIME: or ;PRINT.TIME: in header to match final TIME_ELAPSED.
        
        Args:
            combined: List of G-code lines including header
            
        Returns:
            Updated list with corrected header time value
        """
        try:
            # Find the last TIME_ELAPSED value in the entire G-code
            last_time = None
            for line in reversed(combined):
                if ';TIME_ELAPSED:' in line:
                    try:
                        last_time = float(line.split(':')[1])
                        break
                    except (ValueError, IndexError):
                        pass
            
            if last_time is None:
                Logger.log("w", "Could not find TIME_ELAPSED values to update header time")
                return combined
            
            # Update header - look for ;TIME: or ;PRINT.TIME:
            # Be careful not to match ;TIME_ELAPSED:
            time_updated = False
            for i, line in enumerate(combined):
                line_stripped = line.strip()
                
                # Match ;TIME: but NOT ;TIME_ELAPSED:
                if line_stripped.startswith(';TIME:') and not line_stripped.startswith(';TIME_ELAPSED:'):
                    combined[i] = f";TIME:{int(last_time)}\n"
                    time_updated = True
                    break
                elif line_stripped.startswith(';PRINT.TIME:'):
                    combined[i] = f";PRINT.TIME:{int(last_time)}\n"
                    time_updated = True
                    break
                
                # Stop searching after we leave the header section
                if ';END_OF_HEADER' in line_stripped or 'START_OF_HEADER' in line_stripped:
                    # Some G-code files might have these markers
                    pass
                elif line_stripped.startswith('G') or line_stripped.startswith('M'):
                    # Reached actual G-code commands, stop searching
                    break
            
            if not time_updated:
                Logger.log("w", "Could not find ;TIME: or ;PRINT.TIME: in header to update")
            
            return combined
            
        except Exception as e:
            Logger.log("e", f"Error updating header time: {str(e)}")
            return combined
