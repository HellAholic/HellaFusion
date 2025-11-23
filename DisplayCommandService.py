"""Service for updating M117/M118 LCD display commands in G-code.

This service handles post-processing of display commands after fusion, updating:
- Layer numbers (sections are renumbered consecutively)
- Time estimates (based on adjusted TIME_ELAPSED values)
"""

from UM.Logger import Logger


class DisplayCommandService:
    """Handles updating M117/M118 LCD display commands with correct layer and time info."""
    
    def updateDisplayCommands(self, combined: list) -> list:
        """Update M117/M118 LCD display commands with correct layer numbers and adjusted times.
        
        Post-processing scripts like "Display Info on LCD" add M117/M118 commands to show progress.
        After fusion, these need updating because:
        - Layer numbers change (sections are renumbered consecutively)
        - Time estimates change (we adjust TIME_ELAPSED values)
        
        Formats to update:
        - Display Progress: "M117 45/80 | ET 2h13m" or "M117 45/80 | TP 1h30m"
        - Filename and Layer: "M117 Printing Layer 45 of 80 filename"
        
        Args:
            combined: List of G-code lines with M117/M118 commands
            
        Returns:
            Updated list with corrected M117/M118 commands
        """
        try:
            # Count total layers in fused file
            total_layers = 0
            for line in combined:
                if line.strip().startswith(';LAYER:'):
                    total_layers += 1
            
            if total_layers == 0:
                Logger.log("w", "No layers found for M117/M118 update")
                return combined
            
            current_layer = 0
            m117_count = 0
            m118_count = 0
            
            for i, line in enumerate(combined):
                line_stripped = line.strip()
                
                # Track current layer number
                if line_stripped.startswith(';LAYER:'):
                    try:
                        current_layer = int(line_stripped.split(':')[1]) + 1  # Convert to 1-based
                    except (ValueError, IndexError):
                        pass
                
                # Update M117 commands
                if line_stripped.startswith('M117'):
                    updated_line = self.updateDisplayCommand(line_stripped, current_layer, total_layers, combined, i)
                    if updated_line != line_stripped:
                        combined[i] = updated_line + '\n'
                        m117_count += 1
                
                # Update M118 commands  
                elif line_stripped.startswith('M118'):
                    updated_line = self.updateDisplayCommand(line_stripped, current_layer, total_layers, combined, i)
                    if updated_line != line_stripped:
                        combined[i] = updated_line + '\n'
                        m118_count += 1
            
            return combined
            
        except Exception as e:
            Logger.log("e", f"Error updating display commands: {str(e)}")
            return combined
    
    def updateDisplayCommand(self, command: str, current_layer: int, total_layers: int, combined: list, line_index: int) -> str:
        """Update a single M117/M118 command with correct layer number and time.
        
        Args:
            command: Original M117 or M118 command line
            current_layer: Current layer number (1-based)
            total_layers: Total number of layers in fused file
            combined: Full G-code list (to find TIME_ELAPSED)
            line_index: Index of this command in combined list
            
        Returns:
            Updated command string
        """
        import re
        
        # Extract command prefix (M117 or M118 with optional parameters like A1, P0)
        cmd_match = re.match(r'(M11[78](?:\s+[AP]\d+)*)\s+(.+)', command)
        if not cmd_match:
            return command
        
        cmd_prefix = cmd_match.group(1)
        message = cmd_match.group(2)
        
        # Pattern 1: Display Progress format "45/80 | ET 2h13m" or "45/80 | TP 1h30m"
        progress_match = re.match(r'(\d+)/(\d+)\s+\|\s+(ET|TP)\s+(.+)', message)
        if progress_match:
            # Update layer numbers
            new_message = f"{current_layer}/{total_layers} | {progress_match.group(3)} "
            
            # Find the TIME_ELAPSED for this layer and total print time
            time_elapsed = self.findTimeElapsedForLayer(combined, line_index)
            total_time = self.findTotalPrintTime(combined)
            
            if total_time is not None:
                # If no TIME_ELAPSED found (e.g., layer 0), assume elapsed = 0
                if time_elapsed is None:
                    time_elapsed = 0.0
                
                # ET shows REMAINING time (total - elapsed)
                remaining_time = total_time - time_elapsed
                time_str = self.formatTimeDisplay(remaining_time)
                new_message += time_str
            else:
                # Keep original time if we can't find total time
                new_message += progress_match.group(4)
            
            return f"{cmd_prefix} {new_message}"
        
        # Pattern 2: Filename and Layer format "Printing Layer 45 of 80 filename"
        filename_match = re.match(r'(Printing\s+)?Layer\s+(\d+)(\s+of\s+(\d+))?(.+)?', message)
        if filename_match:
            prefix_text = filename_match.group(1) or ""
            has_total = filename_match.group(3) is not None
            suffix_text = filename_match.group(5) or ""
            
            if has_total:
                new_message = f"{prefix_text}Layer {current_layer} of {total_layers}{suffix_text}"
            else:
                new_message = f"{prefix_text}Layer {current_layer}{suffix_text}"
            
            return f"{cmd_prefix} {new_message}"
        
        # Pattern 3: Header time display format "ET 0 hr 37 min" or "Adjusted Print Time is 0 hr 37 min"
        # These appear in the header before any layers and should show total print time
        header_time_match = re.match(r'(.*?)(ET|Adjusted Print Time is)\s+(.+)', message)
        if header_time_match:
            prefix_text = header_time_match.group(1)
            time_label = header_time_match.group(2)
            
            total_time = self.findTotalPrintTime(combined)
            if total_time is not None:
                # Format total time in hours and minutes like "1 hr 55 min"
                hours = int(total_time // 3600)
                minutes = int((total_time % 3600) // 60)
                if hours > 0:
                    time_str = f"{hours} hr {minutes} min"
                else:
                    time_str = f"{minutes} min"
                
                new_message = f"{prefix_text}{time_label} {time_str}"
                return f"{cmd_prefix} {new_message}"
        
        # If no pattern matched, return original
        return command
    
    def findTimeElapsedForLayer(self, combined: list, start_index: int) -> float:
        """Find the TIME_ELAPSED value for the layer containing the given line index.
        
        Searches backward from start_index to find the most recent TIME_ELAPSED comment.
        The TIME_ELAPSED appears just before the ;LAYER: marker, so we need to find it
        before hitting the PREVIOUS layer's marker.
        
        Args:
            combined: Full G-code list
            start_index: Index to start searching from
            
        Returns:
            Time in seconds, or None if not found
        """
        # Search backward from the current position to find TIME_ELAPSED
        layer_count = 0
        for i in range(start_index, -1, -1):
            line = combined[i].strip()
            if line.startswith(';TIME_ELAPSED:'):
                try:
                    return float(line.split(':')[1])
                except (ValueError, IndexError):
                    pass
            # Count ;LAYER: markers - stop if we've passed TWO layers back
            # (first one is current layer, second would be previous layer)
            if line.startswith(';LAYER:'):
                layer_count += 1
                if layer_count >= 2:
                    break
        return None
    
    def findTotalPrintTime(self, combined: list) -> float:
        """Find the total print time from the header.
        
        Searches the header for ;TIME: or ;PRINT.TIME: value.
        
        Args:
            combined: Full G-code list
            
        Returns:
            Total time in seconds, or None if not found
        """
        # Search the first 100 lines for TIME header
        for i in range(min(100, len(combined))):
            line = combined[i].strip()
            # Look for ;TIME: (but not ;TIME_ELAPSED:)
            if line.startswith(';TIME:') and not line.startswith(';TIME_ELAPSED:'):
                try:
                    return float(line.split(':')[1])
                except (ValueError, IndexError):
                    pass
            # Also check for ;PRINT.TIME:
            elif line.startswith(';PRINT.TIME:'):
                try:
                    return float(line.split(':')[1])
                except (ValueError, IndexError):
                    pass
        return None
    
    def formatTimeDisplay(self, seconds: float) -> str:
        """Format seconds into readable time string for LCD display.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string like "2h13m" or "45m" or "3m"
        """
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h{minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return "0m"
