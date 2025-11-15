# HellaFusion Plugin for Cura
# Based on work by GregValiant (Greg Foresi) and HellAholic
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

import re
from UM.Logger import Logger
from cura.CuraApplication import CuraApplication

# Handle both relative and absolute imports for testing
try:
    from .HellaFusionExceptions import FileProcessingError, ValidationError
    from .PluginConstants import PluginConstants
except ImportError:
    # Fallback for direct execution/testing
    from HellaFusionExceptions import FileProcessingError, ValidationError
    from PluginConstants import PluginConstants


class HellaFusionLogic:
    """Core logic for extracting Z height ranges and combining gcode sections."""
    
    def __init__(self):
        self._retraction_enabled = True
        self._retraction_retract_speed = 2100
        self._retraction_prime_speed = 2100
        self._relative_extrusion = False
        self._firmware_retraction = False
        self._retraction_amount = 4.5
        self._speed_z_hop = 600
        self._speed_travel = 3000
        self._script_hop_height = 0.4
        self._layer_height = 0.2
        
        self._loadCuraSettings()
    
    def _loadCuraSettings(self):
        """Load relevant settings from Cura."""
        try:
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            
            if global_stack:
                extruders = global_stack.extruderList
                if extruders:
                    self._retraction_enabled = bool(extruders[0].getProperty("retraction_enable", "value"))
                    self._firmware_retraction = bool(global_stack.getProperty("machine_firmware_retract", "value"))
                    self._speed_travel = extruders[0].getProperty("speed_travel", "value") * 60
                    self._speed_z_hop = extruders[0].getProperty("speed_z_hop", "value") * 60
                    self._retraction_retract_speed = extruders[0].getProperty("retraction_retract_speed", "value") * 60
                    self._retraction_prime_speed = extruders[0].getProperty("retraction_prime_speed", "value") * 60
                    self._retraction_amount = extruders[0].getProperty("retraction_amount", "value")
                    self._relative_extrusion = global_stack.getProperty("relative_extrusion", "value")
                    self._layer_height = global_stack.getProperty("layer_height", "value")
                    self._initial_layer_height = global_stack.getProperty("initial_layer_height", "value")
                    self._script_hop_height = extruders[0].getProperty("machine_nozzle_size", "value") / 2
        except Exception as e:
            Logger.log("w", f"Error loading Cura settings: {e}")

    def get_current_profile_retraction_settings(self) -> dict:
        """
        Get retraction settings from the currently active profile.
        This should be called after switching to a profile to capture its specific settings.
        
        Returns:
            Dictionary containing retraction settings for the current profile
        """
        settings = {
            'retraction_enabled': True,
            'retraction_amount': 2.0,
            'retraction_speed': 35.0,
            'prime_speed': 30.0,
            'firmware_retraction': False
        }
        
        try:
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            
            if global_stack:
                extruders = global_stack.extruderList
                if extruders:
                    settings['retraction_enabled'] = bool(extruders[0].getProperty("retraction_enable", "value"))
                    settings['retraction_amount'] = float(extruders[0].getProperty("retraction_amount", "value"))
                    settings['retraction_speed'] = float(extruders[0].getProperty("retraction_retract_speed", "value"))
                    settings['prime_speed'] = float(extruders[0].getProperty("retraction_prime_speed", "value"))
                    settings['firmware_retraction'] = bool(global_stack.getProperty("machine_firmware_retract", "value"))
                    
        except Exception as e:
            Logger.log("w", f"Error reading current profile retraction settings: {e}")
            
        return settings
    
    def combineGcodeFiles(self, sections_data: list, output_path: str, calculated_transitions: list = None) -> bool:
        """Combine multiple gcode files into a single spliced file using UNIFIED approach.
        
        Args:
            sections_data: List of dicts with 'section_number', 'gcode_file', 'start_height', 'end_height'
            output_path: Path where the combined gcode will be saved
            calculated_transitions: Pre-calculated transition data from controller (UNIFIED approach)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Read all gcode files
            sections = []
            skipped_sections = []
            
            for section_info in sections_data:
                gcode_lines = self._readGcodeFile(section_info['gcode_file'])
                if not gcode_lines:
                    Logger.log("e", f"Failed to read gcode file: {section_info['gcode_file']}")
                    return False
                
                # Extract section data
                section_data = self._extractSectionData(
                    gcode_lines,
                    section_info['section_number'],
                    section_info['start_height'],
                    section_info['end_height'],
                    section_info.get('layer_height', 0.2),  # Use layer_height from Cura profile
                    section_info.get('profile_retraction_settings')  # Pass retraction settings from profile
                )
                
                if not section_data:
                    Logger.log("e", f"Failed to extract section data for section {section_info['section_number']}")
                    return False
                
                # Check if section has valid gcode (not empty, has actual print moves)
                if not section_data['gcode_lines'] or len(section_data['gcode_lines']) < 5:
                    Logger.log("w", f"Section {section_info['section_number']} has no gcode content (transition height {section_info['start_height']}mm may exceed model height). Skipping this section.")
                    skipped_sections.append(section_info['section_number'])
                    continue
                
                sections.append(section_data)
            
            # Check if we have any valid sections
            if not sections:
                Logger.log("e", "No valid sections found - all transition heights may exceed model height")
                return False
            
            if skipped_sections:
                Logger.log("i", f"Skipped sections: {skipped_sections} (transition heights exceed model height)")
            
            # Pass first gcode file for header extraction
            first_gcode_file = sections_data[0]['gcode_file'] if sections_data else None
            
            # Combine sections using UNIFIED approach
            combined_gcode = self._combineSections(sections, first_gcode_file, calculated_transitions)
            
            if not combined_gcode:
                Logger.log("e", "Failed to combine sections")
                return False
            
            # Write output file
            with open(output_path, 'w', encoding='utf-8') as f:
                for line in combined_gcode:
                    f.write(line)
                    if not line.endswith('\n'):
                        f.write('\n')
            
            return True
            
        except FileProcessingError:
            raise  # Re-raise custom exceptions
        except Exception as e:
            Logger.logException("e", f"Error combining gcode files: {str(e)}")
            raise FileProcessingError(f"Failed to combine gcode files: {str(e)}", operation="combining gcode")
    
    def _readGcodeFile(self, file_path: str) -> list:
        """Read a gcode file and return lines as a list."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            return lines
        except Exception as e:
            Logger.logException("e", f"Error reading gcode file {file_path}: {str(e)}")
            return []
    
    def _extractSectionData(self, gcode_lines: list, section_number: int, start_height: float, end_height: float, layer_height: float = 0.2, retraction_settings: dict = None) -> dict:
        """Extract section data from a specific Z height range.
        
        Each temp file contains the FULL model sliced with one profile.
        We extract just the Z range needed for this section.
        
        Example:
          File 1: Full model (0-20mm) sliced with 0.2mm layers
          File 2: Full model (0-20mm) sliced with 0.1mm layers
          File 3: Full model (0-20mm) sliced with 0.3mm layers
          
          Section 1: Extract Z=0-5mm from File 1
          Section 2: Extract Z=5-10mm from File 2
          Section 3: Extract Z=10-20mm from File 3
        
        Z coordinates are already correct and continuous in each file!
        
        Args:
            layer_height: Layer height from Cura profile (more reliable than detection)
        
        Returns a dict with:
        - section_number
        - gcode_lines: Gcode lines for this Z range
        - start_z, end_z: Z boundaries
        - start_position, end_position: Dict with x, y, z, e
        - layer_height: Layer height from Cura profile
        - is_retracted_at_start: Based on profile's retraction_enabled setting
        - is_retracted_at_end: Based on profile's retraction_enabled setting (same as start)
        """
        try:
            # Determine retraction state from profile settings
            # If retraction is enabled in the profile, the section is retracted at both start and end
            # If retraction is disabled, the section is not retracted at either start or end
            retraction_enabled = True
            if retraction_settings:
                retraction_enabled = retraction_settings.get('retraction_enabled', True)
            else:
                Logger.log("w", f"Section {section_number}: No retraction settings provided, defaulting to enabled=True")
            
            section_data = {
                'section_number': section_number,
                'gcode_lines': [],
                'start_z': start_height,
                'end_z': end_height,
                'start_position': {'x': 0, 'y': 0, 'z': 0, 'e': 0},
                'end_position': {'x': 0, 'y': 0, 'z': 0, 'e': 0},
                'layer_height': layer_height,  # Use layer_height from Cura profile
                'is_retracted_at_start': retraction_enabled,  # Retracted at start if profile has retraction enabled
                'is_retracted_at_end': retraction_enabled,    # Retracted at end if profile has retraction enabled
                'profile_retraction_settings': retraction_settings
            }
            
            current_z = 0.0
            current_x = 0.0
            current_y = 0.0
            current_e = 0.0
            prev_z = 0.0
            is_retracted = False
            
            in_section = False
            in_header = False
            past_startup = False
            
            # Smart layer alignment: track the Z of the current layer being printed
            current_layer_z = 0.0  # The Z height where the current layer prints
            last_layer_final_z = 0.0  # Track the final Z at end of previous layer
            min_z_in_layer = None  # Track minimum Z seen in current layer (to ignore Z-hops)
            last_z_move_line = None  # Buffer to hold the last Z move before layer marker
            
            for i, line in enumerate(gcode_lines):
                line_stripped = line.strip()
                
                # Skip header block
                if ';START_OF_HEADER' in line_stripped:
                    in_header = True
                if in_header:
                    if ';END_OF_HEADER' in line_stripped:
                        in_header = False
                    continue
                
                # Handle `;LAYER:` marker - this marks the start of a new layer
                if ';LAYER:' in line_stripped:
                    if not past_startup:
                        past_startup = True
                        # CRITICAL: Reset Z position tracking!
                        # Startup G0 Z20.001 is NOT part of the print - reset to 0
                        current_z = 0.0
                        prev_z = 0.0
                        # Don't reset current_layer_z - let it be set from min_z_in_layer
                        min_z_in_layer = None
                        last_layer_final_z = 0.0
                        # Don't continue - fall through to process layer marker logic below
                    
                    # Update current_layer_z from previous layer's min_z (works for all layers including LAYER:0)
                    # Use min_z_in_layer if set, otherwise fall back to current_z (for layers with no Z moves)
                    layer_z = min_z_in_layer if min_z_in_layer is not None else current_z
                    if layer_z > 0:
                        # No need to detect layer height - we get it from Cura profile now!
                        current_layer_z = layer_z
                        last_layer_final_z = layer_z
                    # Reset for tracking this new layer
                    min_z_in_layer = None
                
                # Handle startup section
                if not past_startup:
                    # Still in startup - track X, Y, E but NOT Z!
                    # (Z during startup is for homing/clearance, not printing)
                    if ' X' in line_stripped and self._getValue(line_stripped, 'X') is not None:
                        current_x = self._getValue(line_stripped, 'X')
                    if ' Y' in line_stripped and self._getValue(line_stripped, 'Y') is not None:
                        current_y = self._getValue(line_stripped, 'Y')
                    if ' E' in line_stripped and self._getValue(line_stripped, 'E') is not None:
                        current_e = self._getValue(line_stripped, 'E')
                    
                    # For Section 1 ONLY, collect startup commands
                    if section_number == 1 and start_height == 0:
                        section_data['gcode_lines'].append(line if line.endswith('\n') else line + '\n')
                    
                    continue  # Skip to next line
                
                # Track position changes
                if ' Z' in line_stripped and self._getValue(line_stripped, 'Z') is not None:
                    new_z = self._getValue(line_stripped, 'Z')
                    prev_z = current_z
                    current_z = new_z
                    # Buffer this Z move - we may need to include it when starting a section
                    last_z_move_line = line if line.endswith('\n') else line + '\n'
                    
                    # Track minimum Z in current layer (to ignore Z-hops)
                    if past_startup:
                        if min_z_in_layer is None or new_z < min_z_in_layer:
                            min_z_in_layer = new_z
                
                if ' X' in line_stripped and self._getValue(line_stripped, 'X') is not None:
                    current_x = self._getValue(line_stripped, 'X')
                if ' Y' in line_stripped and self._getValue(line_stripped, 'Y') is not None:
                    current_y = self._getValue(line_stripped, 'Y')
                
                # Track E and retraction state
                if ' E' in line_stripped and self._getValue(line_stripped, 'E') is not None:
                    e_val = self._getValue(line_stripped, 'E')
                    if self._relative_extrusion:
                        if e_val < 0:
                            is_retracted = True
                        elif e_val > 0:
                            is_retracted = False
                    else:
                        if e_val < current_e:
                            is_retracted = True
                        elif e_val > current_e:
                            is_retracted = False
                        current_e = e_val
                
                # SMART LAYER ALIGNMENT: Extract ±5mm around boundary for alignment
                # This gives the alignment algorithm enough layers to find optimal transitions
                
                # Start section extraction at boundary - 5mm (or from beginning for section 1)
                search_range_mm = 5.0
                extraction_start = max(0, start_height - search_range_mm)  # Don't go below Z=0
                
                start_condition = (current_layer_z >= extraction_start)
                if not in_section and past_startup and ';LAYER:' in line_stripped and start_condition:
                    in_section = True
                    section_data['start_position'] = {
                        'x': current_x, 'y': current_y, 'z': current_layer_z, 'e': current_e
                    }
                    # Retraction state now determined from profile settings, not G-code analysis
                    # section_data['is_retracted_at_start'] = is_retracted
                
                # End section when we see a layer beyond reasonable range of boundary
                # Extract generously - we'll trim to exact alignment during combination
                if in_section and end_height is not None and ';LAYER:' in line_stripped:
                    # Extract layers up to 2x layer_height beyond boundary to have options for alignment
                    layer_height = section_data.get('layer_height', 0.2)
                    max_z = end_height + (layer_height * 2)
                    if current_layer_z > max_z:
                        break
                
                # Collect lines while in section
                if in_section:
                    section_data['gcode_lines'].append(line if line.endswith('\n') else line + '\n')
                    
                    # Update end state
                    section_data['end_position'] = {
                        'x': current_x, 'y': current_y, 'z': current_z, 'e': current_e
                    }
                    # Retraction state now determined from profile settings, not G-code analysis
                    # section_data['is_retracted_at_end'] = is_retracted
            
            # Check if section was never entered - this is important for user feedback
            if not in_section:
                Logger.log("w", f"Section {section_number} start height {start_height}mm was never reached (model max Z: {current_z:.2f}mm)")
            
            return section_data
            
        except Exception as e:
            Logger.logException("e", f"Error extracting section data: {str(e)}")
            return None
    
    def _trimSectionToZ(self, section: dict, min_z: float = None, max_z: float = None) -> dict:
        """Trim section to only include layers within Z range [min_z, max_z].
        
        For sections 2+, this method:
        1. Finds the reference layer (at boundary Z) and extracts final XYE values
        2. Removes the reference layer from output (it should not print)
        3. Keeps only layers that should actually print
        
        Layers are identified by their printing height (minimum Z in layer, ignoring Z-hops).
        
        Args:
            section: Section data dict
            min_z: Minimum layer Z to include (None = no minimum)
            max_z: Maximum layer Z to include (None = no maximum)
        
        Returns new section dict with trimmed gcode_lines and updated positions.
        """

        trimmed_lines = []
        in_valid_layer = False
        startup_done = False
        current_layer_z = None
        min_z_in_current_layer = None
        pending_layer_marker = None  # Buffer layer marker until we know if layer is valid
        
        # For section 1 (min_z = None), include startup
        # For sections 2+ (min_z set), skip startup entirely
        include_startup = (min_z is None)
        
        first_layer_seen = False  # Track if we've seen the first layer
        
        # Track reference layer data (for extracting XYE values before excluding it)
        reference_layer_z = min_z  # The boundary Z where reference layer prints
        reference_layer_lines = []  # Store reference layer lines for extraction
        in_reference_layer = False
        reference_layer_extracted = False
        
        for line in section['gcode_lines']:
            line_stripped = line.strip()
            
            # Handle startup (before first ;LAYER:)
            if not startup_done:
                if ';LAYER:' in line_stripped:
                    startup_done = True
                    first_layer_seen = True
                    pending_layer_marker = line  # Buffer this layer marker
                    # For section 1 (min_z = None), first layer is automatically valid
                    if min_z is None:
                        in_valid_layer = True
                    # For other sections, wait for Z tracking to determine validity
                elif include_startup:
                    trimmed_lines.append(line)
                continue
            
            # New layer marker
            if ';LAYER:' in line_stripped:
                # First, process any pending reference layer
                if in_reference_layer and reference_layer_lines:
                    # Extract reference values from the layer we're about to exclude
                    self._extractReferenceFromLayer(section, reference_layer_lines, reference_layer_z)
                    reference_layer_extracted = True
                    # Don't add reference layer to output - it should be excluded
                    reference_layer_lines = []
                    in_reference_layer = False
                
                # Check if previous pending layer should be included
                if pending_layer_marker and in_valid_layer:
                    trimmed_lines.append(pending_layer_marker)
                
                # Determine current layer's Z from previous tracking
                if min_z_in_current_layer is not None:
                    current_layer_z = min_z_in_current_layer
                
                # Reset for new layer
                min_z_in_current_layer = None
                pending_layer_marker = line  # Buffer this new layer marker
                first_layer_seen = False
                
                # Check if this is the reference layer (should be extracted but not included)
                if (current_layer_z is not None and reference_layer_z is not None and 
                    abs(current_layer_z - reference_layer_z) < 0.001):
                    in_reference_layer = True
                    in_valid_layer = False  # Don't include in output
                else:
                    # Check if this layer is in the valid range to include
                    if current_layer_z is not None:
                        in_valid_layer = True
                        if min_z is not None and current_layer_z < min_z:
                            in_valid_layer = False
                        if max_z is not None and current_layer_z > max_z:
                            in_valid_layer = False
                            break  # Stop, we're past the max
                    else:
                        # First layer for section 1
                        in_valid_layer = (min_z is None)
                
                continue
            
            # Track Z moves to find layer height
            match = re.search(r' Z(\d+\.?\d*)', line_stripped)
            if match:
                z = float(match.group(1))
                if min_z_in_current_layer is None or z < min_z_in_current_layer:
                    min_z_in_current_layer = z
                
                # Once we see the first Z move in the first layer, we can determine if it's valid
                if first_layer_seen and current_layer_z is None:
                    current_layer_z = z
                    # Check if this is the reference layer
                    if (reference_layer_z is not None and abs(z - reference_layer_z) < 0.001):
                        in_reference_layer = True
                        in_valid_layer = False
                    else:
                        # Check if first layer is in range
                        in_valid_layer = True
                        if min_z is not None and z < min_z:
                            in_valid_layer = False
                        if max_z is not None and z > max_z:
                            in_valid_layer = False
                    first_layer_seen = False  # Don't check again
            
            # Store reference layer lines for extraction
            if in_reference_layer:
                reference_layer_lines.append(line)
                continue
            
            # Include line if we're in a valid layer
            if in_valid_layer:
                # If this is the first line of a valid layer, add the pending marker first
                if pending_layer_marker:
                    trimmed_lines.append(pending_layer_marker)
                    pending_layer_marker = None
                trimmed_lines.append(line)
        
        # Update section data - use dict copy to preserve all fields including layer_height
        trimmed_section = {
            'section_number': section['section_number'],
            'start_z': section['start_z'],
            'end_z': section['end_z'],
            'start_position': section['start_position'].copy(),
            'end_position': section['end_position'].copy(),
            'layer_height': section['layer_height'],  # Preserve detected layer height!
            'is_retracted_at_start': section['is_retracted_at_start'],
            'is_retracted_at_end': section['is_retracted_at_end'],
            'profile_retraction_settings': section.get('profile_retraction_settings'),
            'gcode_lines': trimmed_lines
        }
        
        # Update end/start positions based on actual trim points
        if max_z is not None:
            trimmed_section['end_position']['z'] = max_z
        if min_z is not None:
            trimmed_section['start_position']['z'] = min_z
        
        # Scan for actual XYE positions at END boundary (scan backwards)
        for line in reversed(trimmed_lines):
            if line.strip().startswith(('G0', 'G1')):
                match_x = re.search(r' X(\d+\.?\d*)', line)
                match_y = re.search(r' Y(\d+\.?\d*)', line)
                match_e = re.search(r' E(-?\d+\.?\d*)', line)
                if match_x:
                    trimmed_section['end_position']['x'] = float(match_x.group(1))
                if match_y:
                    trimmed_section['end_position']['y'] = float(match_y.group(1))
                if match_e:
                    trimmed_section['end_position']['e'] = float(match_e.group(1))
                break
        
        return trimmed_section
    
    def _extractReferenceFromLayer(self, section: dict, reference_layer_lines: list, reference_z: float) -> None:
        """Extract XYE values from the reference layer lines and update section's start_position.
        
        This method processes the reference layer (that will be excluded from output) to get
        the final XYE position that should be used for the transition.
        
        Args:
            section: Section data dict to update with reference values
            reference_layer_lines: List of gcode lines from the reference layer
            reference_z: Z height of the reference layer
        """
        import re
        
        # Extract the final XYE values from the reference layer
        final_x = None
        final_y = None
        final_e = None
        
        # Scan through the reference layer lines to find the last XYE values
        for line in reference_layer_lines:
            line_stripped = line.strip()
            
            if line_stripped.startswith(('G0', 'G1')):
                match_x = re.search(r' X(\d+\.?\d*)', line_stripped)
                match_y = re.search(r' Y(\d+\.?\d*)', line_stripped)
                match_e = re.search(r' E(-?\d+\.?\d*)', line_stripped)
                
                if match_x:
                    final_x = float(match_x.group(1))
                if match_y:
                    final_y = float(match_y.group(1))
                if match_e:
                    final_e = float(match_e.group(1))
        
        # Update the section's start_position with the reference values
        if final_x is not None:
            section['start_position']['x'] = final_x
        if final_y is not None:
            section['start_position']['y'] = final_y
        if final_e is not None:
            section['start_position']['e'] = final_e
        
        # Set the Z to the reference layer's Z height
        section['start_position']['z'] = reference_z
    
    def _extractPreviousLayerValues(self, section: dict, target_z: float) -> dict:
        """Extract XYE values from the layer that matches the actual transition Z height.
        
        This finds where the nozzle actually is at the end of the previous section,
        using the ACTUAL transition Z calculated by the closest layer detection algorithm.
        We scan the ORIGINAL section gcode (before trimming) to find this layer.
        
        Args:
            section: Section data dict (NOT YET TRIMMED - still has all layers)  
            target_z: The ACTUAL transition Z height (not user boundary) where sections meet
        
        Returns: Updated section dict with start_position set to correct layer's last XYE,
                 ensuring continuous progression between sections
        """
        import re
        
        # Find the layer that matches target_z (this will be the first layer after trimming)
        target_layer_num = None
        prev_layer_num = None
        current_layer_num = None
        layer_z_map = {}  # Map layer numbers to their Z heights
        
        # Build a map of layer numbers to Z heights
        for line in section['gcode_lines']:
            line_stripped = line.strip()
            if ';LAYER:' in line_stripped:
                layer_match = re.search(r';LAYER:(\d+)', line_stripped)
                if layer_match:
                    current_layer_num = int(layer_match.group(1))
            elif current_layer_num is not None and ' Z' in line_stripped:
                match_z = re.search(r' Z(\d+\.?\d*)', line_stripped)
                if match_z:
                    z = float(match_z.group(1))
                    if current_layer_num not in layer_z_map:
                        layer_z_map[current_layer_num] = z
        
        # Find the layer number that corresponds to target_z
        # This is the layer that STARTS at target_z, which is where section will be trimmed to start
        # We want the END values from this layer to use for the transition
        target_layer_num = None
        for layer_num, layer_z in layer_z_map.items():
            if abs(layer_z - target_z) < 0.001:  # Found the layer that starts at target_z
                target_layer_num = layer_num
                break
        
        if target_layer_num is None or target_layer_num == 0:
            return section
        
        # We want XYE values from the END of this layer (where the layer finishes before the next layer starts)
        # This is the layer that will be trimmed away, so we use its END position for the transition
        # However, if this layer has no extrusion (empty layer with only travels), look at previous layer
        prev_layer_num = target_layer_num
        prev_layer_x = None
        prev_layer_y = None
        prev_layer_e = None
        in_prev_layer = False
        
        for line in section['gcode_lines']:  # Scan the current gcode_lines
            line_stripped = line.strip()
            
            # Track when we enter/exit layers
            if ';LAYER:' in line_stripped:
                layer_match = re.search(r';LAYER:(\d+)', line_stripped)
                if layer_match:
                    layer_num = int(layer_match.group(1))
                    if layer_num == prev_layer_num:
                        in_prev_layer = True
                    elif in_prev_layer and layer_num > prev_layer_num:
                        # Reached next layer after our target, stop scanning
                        break
            
            # Collect LAST XYE from previous layer
            if in_prev_layer and line_stripped.startswith(('G0', 'G1')):
                match_x = re.search(r' X(\d+\.?\d*)', line_stripped)
                match_y = re.search(r' Y(\d+\.?\d*)', line_stripped)
                match_e = re.search(r' E(-?\d+\.?\d*)', line_stripped)
                
                if match_x:
                    prev_layer_x = float(match_x.group(1))
                if match_y:
                    prev_layer_y = float(match_y.group(1))
                if match_e:
                    prev_layer_e = float(match_e.group(1))
        
        # If we didn't find an E value (empty layer with only travel moves), look at the previous layer
        if prev_layer_e is None and prev_layer_num > 0:
            prev_layer_num = prev_layer_num - 1
            in_prev_layer = False
            
            for line in section['gcode_lines']:
                line_stripped = line.strip()
                
                if ';LAYER:' in line_stripped:
                    layer_match = re.search(r';LAYER:(\d+)', line_stripped)
                    if layer_match:
                        layer_num = int(layer_match.group(1))
                        if layer_num == prev_layer_num:
                            in_prev_layer = True
                        elif in_prev_layer and layer_num > prev_layer_num:
                            break
                
                if in_prev_layer and line_stripped.startswith(('G0', 'G1')):
                    match_x = re.search(r' X(\d+\.?\d*)', line_stripped)
                    match_y = re.search(r' Y(\d+\.?\d*)', line_stripped)
                    match_e = re.search(r' E(-?\d+\.?\d*)', line_stripped)
                    
                    if match_x:
                        prev_layer_x = float(match_x.group(1))
                    if match_y:
                        prev_layer_y = float(match_y.group(1))
                    if match_e:
                        prev_layer_e = float(match_e.group(1))
        
        # Update start_position
        if prev_layer_x is not None:
            section['start_position']['x'] = prev_layer_x
        if prev_layer_y is not None:
            section['start_position']['y'] = prev_layer_y
        if prev_layer_e is not None:
            section['start_position']['e'] = prev_layer_e
        
        return section
    
    def _findAlignmentPoint(self, section_a: dict, section_b: dict, boundary: float) -> tuple:
        """DEPRECATED: Old alignment search method - kept as fallback only.
        
        The UNIFIED approach now uses pre-calculated transitions from the controller
        instead of this search-based alignment. This method should only be called
        if the calculated_transitions are not available (error condition).
        
        Find perfect layer alignment between two sections near the boundary.
        
        The key insight: layers must align like puzzle pieces. If section A ends at Z1,
        section B must start at Z2 where (Z2 - Z1) = section B's layer height exactly.
        
        NEW PRIORITIZATION LOGIC:
        1. First, find all matches with perfect gap alignment (gap_error < 0.001mm)
        2. Among perfect matches, choose the one CLOSEST to the boundary
        3. If no perfect matches, find matches with acceptable gap (gap_error < 0.02mm)
        4. Among acceptable matches, prioritize:
           a) Gap quality (smaller gap_error is better)
           b) Boundary proximity (closer to boundary is better)
        5. Layers above or below boundary are equally valid
        
        Returns (end_z_for_a, start_z_for_b) tuple.
        """
        import re
        
        # Get layer heights
        lh_a = section_a.get('layer_height', 0.2)
        lh_b = section_b.get('layer_height', 0.2)
        
        # Extract unique Z values from both sections (actual printing heights, not Z-hops)
        def extract_layer_z_values(gcode_lines):
            z_values = []
            in_layer = False
            min_z_in_layer = None
            
            for line in gcode_lines:
                if ';LAYER:' in line:
                    if min_z_in_layer is not None:
                        z_values.append(min_z_in_layer)
                    min_z_in_layer = None
                    in_layer = True
                    continue
                    
                if in_layer:
                    match = re.search(r' Z(\d+\.?\d*)', line)
                    if match:
                        z = float(match.group(1))
                        if min_z_in_layer is None or z < min_z_in_layer:
                            min_z_in_layer = z
            
            if min_z_in_layer is not None:
                z_values.append(min_z_in_layer)
            
            return sorted(set(z_values))
        
        layers_a = extract_layer_z_values(section_a['gcode_lines'])
        layers_b = extract_layer_z_values(section_b['gcode_lines'])
        
        # With initial layer height adjustments, we should find perfect matches close to boundary
        # Use tighter search range - matches should be within a few layer heights
        search_range_mm = max(lh_a, lh_b) * 3  # Search within 3 layer heights
                
        # Find all candidate matches with gap alignment score
        # With initial layer height adjustments, we expect perfect or near-perfect matches
        tolerance = 0.02  # Maximum acceptable gap error (mm)
        perfect_threshold = 0.001  # Gap error threshold for "perfect" match
        
        all_matches = []
        
        for z_a in layers_a:
            # Consider layers within search range
            if abs(z_a - boundary) > search_range_mm:
                continue
            
            for z_b in layers_b:
                # Calculate gap error: how far is (z_b - z_a) from ideal layer_height_b?
                gap_error = abs((z_b - z_a) - lh_b)
                
                # Calculate boundary distance: how far is z_a from the target boundary?
                boundary_distance = abs(z_a - boundary)
                
                # Store all matches regardless of gap error (we'll filter later)
                all_matches.append({
                    'z_a': z_a,
                    'z_b': z_b,
                    'gap_error': gap_error,
                    'boundary_distance': boundary_distance,
                    'gap': z_b - z_a
                })
        
        if not all_matches:
            # Last resort fallback: use layers closest to boundary
            end_a = max([z for z in layers_a if z <= boundary + lh_a], default=layers_a[-1])
            start_b = min([z for z in layers_b if z >= boundary], default=layers_b[0])
            return (end_a, start_b)
        
        # STRATEGY 1: With initial layer height adjustments, find the layer of Section A
        # that's CLOSEST to the boundary, then find Section B's first layer that creates
        # a proper gap. NOTE: The gap may not match layer_height_b exactly because the
        # first layer of Section B has an adjusted initial layer height.
        
        # Find Section A layers closest to boundary (prefer AT or just below boundary)
        layers_a_near_boundary = [z for z in layers_a if abs(z - boundary) <= max(lh_a, lh_b)]
        layers_a_near_boundary.sort(key=lambda z: abs(z - boundary))
        
        if layers_a_near_boundary:
            # Try each candidate ending point for Section A, prioritizing boundary proximity
            for end_z_a in layers_a_near_boundary:
                # Find the FIRST layer of Section B at or above this ending point
                candidate_starts_b = [z for z in layers_b if z >= end_z_a]
                
                if candidate_starts_b:
                    start_z_b = candidate_starts_b[0]  # First layer at or above end of A
                    gap = start_z_b - end_z_a
                    boundary_distance = abs(end_z_a - boundary)
                    
                    # Accept if very close to boundary - the gap will be whatever the adjusted
                    # initial layer height dictates, which may differ from layer_height_b
                    if boundary_distance <= tolerance:  # Within 0.02mm of boundary
                        return (end_z_a, start_z_b)
        
        # Fallback: Try perfect matches from original logic
        perfect_matches = [m for m in all_matches if m['gap_error'] < perfect_threshold]
        
        if perfect_matches:
            # Sort by boundary_distance - we want the closest to user-defined height
            perfect_matches.sort(key=lambda x: x['boundary_distance'])
            best = perfect_matches[0]
            return (best['z_a'], best['z_b'])
        
        # STRATEGY 2: Find near-perfect matches (gap_error < tolerance) closest to boundary
        # Sort by boundary_distance first to get closest to target height
        acceptable_matches = [m for m in all_matches if m['gap_error'] < tolerance]
        
        if acceptable_matches:
            # Sort by boundary_distance first (closest to target), then gap quality
            acceptable_matches.sort(key=lambda x: (x['boundary_distance'], x['gap_error']))
            best = acceptable_matches[0]
            return (best['z_a'], best['z_b'])
        
        # STRATEGY 3 (FALLBACK): Find best match prioritizing boundary proximity
        # Sort all matches by boundary distance (closest to target height wins)
        all_matches.sort(key=lambda x: (x['boundary_distance'], x['gap_error']))
        best = all_matches[0]
        
        # Only log significant alignment issues
        if best['gap_error'] > tolerance:
            Logger.log("w", f"Layer alignment gap error {best['gap_error']:.3f}mm exceeds tolerance - may cause extrusion issues")
        if best['boundary_distance'] > max(lh_a, lh_b):
            Logger.log("w", f"Transition is {best['boundary_distance']:.3f}mm away from target boundary {boundary:.3f}mm")
        
        return (best['z_a'], best['z_b'])
    
    def _combineSections(self, sections: list, first_gcode_file: str = None, calculated_transitions: list = None) -> list:
        """UNIFIED APPROACH: Combine sections using exact calculated transition points.
        
        This method now uses the pre-calculated transition data from the controller
        instead of searching for alignment points. The controller has already:
        1. Determined exact Z coordinates where transitions occur
        2. Calculated perfect initial layer height adjustments for gap-free transitions
        3. Used iterative pattern matching where each section becomes base for next
        
        Args:
            sections: List of section data dicts from gcode extraction
            first_gcode_file: Path to first gcode file to extract header from
            calculated_transitions: Pre-calculated transition data from controller
        """
        try:
            combined = []
            
            # Add header from first file ONLY
            if first_gcode_file:
                first_gcode = self._readGcodeFile(first_gcode_file)
                if first_gcode:
                    in_header = False
                    for line in first_gcode:
                        line_stripped = line.strip()
                        
                        # Copy header block
                        if ';START_OF_HEADER' in line_stripped:
                            in_header = True
                        if in_header:
                            combined.append(line if line.endswith('\n') else line + '\n')
                            if ';END_OF_HEADER' in line_stripped:
                                in_header = False
                                break  # Stop after header
            
            # Add splicing info
            combined.append("\n;========== GCODE SPLICING INFO ==========\n")
            combined.append(f";Total sections: {len(sections)}\n")
            for section in sections:
                end_str = f"Z{section['end_z']:.2f}mm" if section['end_z'] else "Top"
                combined.append(f";Section {section['section_number']}: Z{section['start_z']:.2f}mm - {end_str}\n")
            combined.append(";=========================================\n\n")
            
            # STEP 1: UNIFIED APPROACH - Use pre-calculated transition points
            alignment_points = []
            
            if calculated_transitions and len(calculated_transitions) == len(sections):
                # Use exact transition points from controller calculation
                for i in range(len(sections) - 1):
                    current_calc = calculated_transitions[i]
                    next_calc = calculated_transitions[i+1]
                    
                    # Get the actual transition Z from calculation (where previous section ACTUALLY ends)
                    end_z_a = current_calc['actual_transition_z'] or current_calc['end_z']
                    
                    # Next section starts at same Z (continuous progression)
                    # Use the same actual transition Z for perfect alignment
                    start_z_b = end_z_a
                    
                    alignment_points.append((i, end_z_a, start_z_b))
            else:
                # Fallback to old search method
                for i in range(len(sections) - 1):
                    boundary = sections[i]['end_z']
                    if boundary:
                        end_z_a, start_z_b = self._findAlignmentPoint(sections[i], sections[i+1], boundary)
                        alignment_points.append((i, end_z_a, start_z_b))
            
            # STEP 2: Build trimming boundaries for each section
            # Each section needs to know its min_z and max_z BEFORE any trimming happens
            trim_boundaries = {}
            for i in range(len(sections)):
                trim_boundaries[i] = {'min_z': None, 'max_z': None}
            
            # Set boundaries from alignment points
            for align_i, end_z_a, start_z_b in alignment_points:
                # Section align_i ends at end_z_a (actual transition Z from closest layer detection)
                trim_boundaries[align_i]['max_z'] = end_z_a
                # Section align_i+1 starts at start_z_b (same as end_z_a for continuous progression)
                # This ensures E values are extracted from the correct layer
                trim_boundaries[align_i + 1]['min_z'] = start_z_b
            
            # STEP 3: For sections 2+, extract XYE values from previous layer BEFORE trimming
            # The previous layer is still in the original section at this point
            for i in range(1, len(sections)):
                start_z_for_this_section = trim_boundaries[i]['min_z']
                if start_z_for_this_section is not None:
                    sections[i] = self._extractPreviousLayerValues(sections[i], start_z_for_this_section)
            
            # STEP 4: Now do the actual trimming - ONCE per section with both min_z and max_z
            for i in range(len(sections)):
                min_z = trim_boundaries[i]['min_z']
                max_z = trim_boundaries[i]['max_z']
                
                # Only trim if there are actual boundaries set
                if min_z is not None or max_z is not None:
                    sections[i] = self._trimSectionToZ(sections[i], min_z, max_z)
            
            # Count total layers AFTER trimming
            current_layer = 0
            total_layers = 0
            for section in sections:
                layer_count = 0
                for line in section['gcode_lines']:
                    if line.strip().startswith(';LAYER:'):
                        layer_count += 1
                total_layers += layer_count
            
            # Add sections with transitions and renumbered layers
            cumulative_time = 0.0  # Track total elapsed time across all sections
            
            # No need to set start states - each section has definitive start/end states from profile settings
            
            for i, section in enumerate(sections):
                combined.append(f";========== SECTION {section['section_number']} START ==========\n")
                
                if i > 0:
                    # Generate transition code with G92 synchronization
                    transition = self._generateTransitionWithG92(sections[i-1], section, calculated_transitions)
                    combined.extend(transition)
                
                # Add section content with renumbered layers and updated time
                # Section 1: Includes startup + printing (already in gcode_lines)
                # Sections 2+: Just printing (startup was skipped by _extractSectionData)
                first_move_in_section = True  # Track if this is the first move command
                section_start_time = None  # Track when this section starts (first TIME_ELAPSED)
                
                for line in section['gcode_lines']:
                    line_stripped = line.strip()
                    
                    # Renumber LAYER_COUNT in startup section
                    if line_stripped.startswith(';LAYER_COUNT:'):
                        combined.append(f";LAYER_COUNT:{total_layers}\n")
                        continue
                    
                    # Renumber layer markers
                    if line_stripped.startswith(';LAYER:'):
                        combined.append(f";LAYER:{current_layer}\n")
                        current_layer += 1
                        continue
                    
                    # Update TIME_ELAPSED comments
                    if line_stripped.startswith(';TIME_ELAPSED:'):
                        try:
                            original_time = float(line_stripped.split(':')[1])
                            # First time marker in section - record section start time
                            if section_start_time is None:
                                section_start_time = original_time
                            # Calculate section-relative time and add to cumulative
                            section_relative_time = original_time - section_start_time
                            adjusted_time = cumulative_time + section_relative_time
                            combined.append(f";TIME_ELAPSED:{adjusted_time:.6f}\n")
                            continue
                        except (ValueError, IndexError):
                            # If parsing fails, keep original line
                            pass
                    
                    # For sections 2+, DON'T strip Z - the extracted section includes the Z move for proper positioning
                    # The transition will handle XY/E, but Z positioning is from the extracted section
                    # (This changed when we implemented smart layer alignment)
                    
                    # Mark that we've passed the first move
                    if line_stripped.startswith(('G0', 'G1')):
                        first_move_in_section = False
                    
                    # Copy all other lines as-is
                    combined.append(line if line.endswith('\n') else line + '\n')
                
                # Update cumulative time for next section
                # Find the last TIME_ELAPSED in this section
                for line in reversed(section['gcode_lines']):
                    if line.strip().startswith(';TIME_ELAPSED:'):
                        try:
                            last_time = float(line.strip().split(':')[1])
                            if section_start_time is not None:
                                section_duration = last_time - section_start_time
                                cumulative_time += section_duration
                        except (ValueError, IndexError):
                            pass
                        break
                
                combined.append(f";========== SECTION {section['section_number']} END ==========\n\n")
            
            return combined
            
        except Exception as e:
            Logger.logException("e", f"Error combining sections: {str(e)}")
            return []
    
    def _shouldPrimeForTransition(self, prev_section: dict, next_section: dict, calculated_transitions: list = None) -> dict:
        """Determine if priming/retracting is needed for the transition based on filament state.
        
        SIMPLIFIED LOGIC:
        Each section's retraction state is determined by its profile's retraction_enabled setting:
        - If retraction_enabled=True: section is retracted at both start and end
        - If retraction_enabled=False: section is not retracted at start or end
        
        Transition decisions:
        a. prev_retracted == next_retracted: no action needed (same state)
        b. prev_retracted=True, next_retracted=False: prime after travel
        c. prev_retracted=False, next_retracted=True: retract before travel
        
        Args:
            prev_section: Previous section data with is_retracted_at_end from profile
            next_section: Next section data with is_retracted_at_start from profile
            calculated_transitions: Pre-calculated transition data
            
        Returns:
            dict with transition decision and parameters:
            {
                'needs_prime': bool,
                'needs_retract': bool,
                'prime_amount': float,
                'retract_amount': float,
                'prime_speed': float,
                'retract_speed': float,
                'reason': str,
                'confidence': str  # 'high', 'medium', 'low'
            }
        """
        decision = {
            'needs_prime': False,
            'needs_retract': False,
            'prime_amount': 0.0,
            'retract_amount': 0.0,
            'prime_speed': self._retraction_prime_speed,  # Will be updated if needed
            'retract_speed': self._retraction_retract_speed,  # Will be updated if needed
            'reason': 'No filament state change needed',
            'confidence': 'high'
        }
        
        # Skip analysis if firmware retraction is enabled
        if self._firmware_retraction:
            decision['reason'] = 'Firmware retraction enabled - handled by firmware'
            return decision
        
        # Get filament states - simplified approach
        # Previous section's end state = its retraction setting
        # Next section's start state = its retraction setting
        prev_retracted = prev_section.get('is_retracted_at_end', False)
        next_retracted = next_section.get('is_retracted_at_start', False)
        
        # Get profile settings for retraction amounts/speeds
        prev_settings = prev_section.get('profile_retraction_settings', {})
        next_settings = next_section.get('profile_retraction_settings', {})
        
        # Case A: Same retraction state - no action needed
        if prev_retracted == next_retracted:
            if prev_retracted:
                decision['reason'] = 'Both sections retracted - no change needed'
            else:
                decision['reason'] = 'Both sections not retracted - no change needed'
            return decision
        
        # Case B: Previous retracted, next not retracted - PRIME needed
        elif prev_retracted and not next_retracted:
            decision['needs_prime'] = True
            
            # Use profile-specific retraction amount from the previous section (the one that was retracted)
            prev_settings = prev_section.get('profile_retraction_settings', {})
            base_amount = prev_settings.get('retraction_amount', self._retraction_amount)
            decision['prime_amount'] = base_amount
            decision['prime_speed'] = prev_settings.get('prime_speed', self._retraction_prime_speed) * 60  # Convert to mm/min
            decision['reason'] = 'Previous section retracted, next section not retracted - prime after travel'
            
            # Apply intelligent adjustments for different conditions
            multiplier = 1.0
            adjustments = []
            
            # Check for quality profile changes
            profile_factor = self._analyzeProfileChanges(prev_section, next_section, calculated_transitions)
            if profile_factor['significant_change']:
                multiplier += profile_factor['adjustment']
                adjustments.append(profile_factor['reason'])
            
            # Check for travel distance
            travel_factor = self._analyzeTravelDistance(prev_section, next_section)
            if travel_factor['long_travel']:
                multiplier += travel_factor['adjustment']
                adjustments.append(travel_factor['reason'])
            
            # Check for Z changes
            z_factor = self._analyzeZChanges(prev_section, next_section)
            if z_factor['significant_change']:
                multiplier += z_factor['adjustment']
                adjustments.append(z_factor['reason'])
            
            # Apply adjustments
            if multiplier != 1.0:
                decision['prime_amount'] = max(
                    PluginConstants.PRIME_MIN_AMOUNT,
                    min(base_amount * multiplier, base_amount * PluginConstants.PRIME_MAX_MULTIPLIER)
                )
                decision['reason'] += f" (adjusted: {'; '.join(adjustments)})"
                decision['confidence'] = 'medium'
        
        # Case C: Previous not retracted, next retracted - RETRACT needed
        elif not prev_retracted and next_retracted:
            decision['needs_retract'] = True
            
            # Use profile-specific retraction amount from the next section (the one that needs to be retracted)
            next_settings = next_section.get('profile_retraction_settings', {})
            decision['retract_amount'] = next_settings.get('retraction_amount', self._retraction_amount)
            decision['retract_speed'] = next_settings.get('retraction_speed', self._retraction_retract_speed) * 60  # Convert to mm/min
            decision['reason'] = 'Previous section not retracted, next section retracted - retract before travel'
            
            # For retractions, we typically don't adjust the amount much
            # But we might adjust based on travel distance or Z changes
            travel_factor = self._analyzeTravelDistance(prev_section, next_section)
            z_factor = self._analyzeZChanges(prev_section, next_section)
            
            adjustments = []
            if travel_factor['long_travel']:
                adjustments.append("long travel distance")
            if z_factor['significant_change']:
                adjustments.append("significant Z change")
            
            if adjustments:
                decision['reason'] += f" ({'; '.join(adjustments)})"
                decision['confidence'] = 'medium'
        
        return decision
    
    def _detectPrimeMoveInSection(self, section: dict) -> bool:
        """Detect if a section has its own prime move after the layer marker."""
        found_layer_marker = False
        for line in section['gcode_lines']:
            line_stripped = line.strip()
            
            if line_stripped.startswith(';LAYER:'):
                found_layer_marker = True
                continue
            
            if found_layer_marker:
                # Skip comments and non-movement commands
                if line_stripped.startswith(';') or line_stripped.startswith('M'):
                    continue
                
                # Check for prime move (G1 with F, E, but no X/Y)
                if line_stripped.startswith('G1') and ' F' in line_stripped and ' E' in line_stripped:
                    if ' X' not in line_stripped and ' Y' not in line_stripped:
                        return True
                # Stop at first movement command
                elif line_stripped.startswith(('G0', 'G1')):
                    break
        
        return False
    
    def _analyzeProfileChanges(self, prev_section: dict, next_section: dict, calculated_transitions: list = None) -> dict:
        """Analyze quality profile changes that might affect priming needs."""
        result = {
            'significant_change': False,
            'adjustment': 0.0,
            'reason': 'No significant profile changes',
            'confidence': 'high'
        }
        
        if not calculated_transitions:
            result['confidence'] = 'low'
            return result
        
        # Find transition data for both sections
        prev_trans = next_trans = None
        for trans in calculated_transitions:
            if trans.get('section_num') == prev_section['section_number']:
                prev_trans = trans
            elif trans.get('section_num') == next_section['section_number']:
                next_trans = trans
        
        if not prev_trans or not next_trans:
            result['confidence'] = 'low'
            return result
        
        # Compare layer heights - significant changes may need extra priming
        prev_layer_height = prev_trans.get('layer_height', 0.2)
        next_layer_height = next_trans.get('layer_height', 0.2)
        layer_height_ratio = next_layer_height / prev_layer_height
        
        if layer_height_ratio > PluginConstants.PRIME_LAYER_HEIGHT_RATIO_HIGH:  # Significantly thicker layers
            result['significant_change'] = True
            result['adjustment'] = 0.2  # 20% more prime
            result['reason'] = f'Layer height increased {layer_height_ratio:.1f}x'
        elif layer_height_ratio < PluginConstants.PRIME_LAYER_HEIGHT_RATIO_LOW:  # Significantly thinner layers
            result['significant_change'] = True
            result['adjustment'] = -0.1  # 10% less prime
            result['reason'] = f'Layer height decreased {layer_height_ratio:.1f}x'
        
        # Compare profile names for quality changes
        prev_profile = prev_trans.get('profile_name', '')
        next_profile = next_trans.get('profile_name', '')
        
        if prev_profile and next_profile and prev_profile != next_profile:
            # Quality profile change detected
            if 'draft' in prev_profile.lower() and 'fine' in next_profile.lower():
                result['significant_change'] = True
                result['adjustment'] += PluginConstants.PRIME_PROFILE_CHANGE_ADJUSTMENT  # More prime for draft->fine
                result['reason'] += '; Draft to Fine quality change'
            elif 'fine' in prev_profile.lower() and 'draft' in next_profile.lower():
                result['significant_change'] = True
                result['adjustment'] += PluginConstants.PRIME_PROFILE_CHANGE_ADJUSTMENT * 0.67  # Moderate prime for fine->draft
                result['reason'] += '; Fine to Draft quality change'
        
        return result
    
    def _analyzeTravelDistance(self, prev_section: dict, next_section: dict) -> dict:
        """Analyze travel distance and estimate time for oozing/cooling effects."""
        result = {
            'long_travel': False,
            'adjustment': 0.0,
            'reason': 'Normal travel distance',
            'confidence': 'high'
        }
        
        prev_pos = prev_section['end_position']
        next_pos = next_section['start_position']
        
        # Calculate 3D travel distance
        xy_distance = ((next_pos['x'] - prev_pos['x'])**2 + (next_pos['y'] - prev_pos['y'])**2)**0.5
        z_distance = abs(next_pos['z'] - prev_pos['z'])
        
        # Consider Z-hop in travel time calculation
        total_distance = xy_distance
        if self._script_hop_height > 0:
            total_distance += 2 * self._script_hop_height  # Up and down
        total_distance += z_distance
        
        # Estimate travel time (very rough approximation)
        travel_time = (xy_distance / (self._speed_travel / 60)) + (z_distance / (self._speed_z_hop / 60))
        
        if xy_distance > PluginConstants.PRIME_LONG_TRAVEL_THRESHOLD:  # Long XY travel
            result['long_travel'] = True
            result['adjustment'] = min(0.15, xy_distance / PluginConstants.PRIME_TRAVEL_ADJUSTMENT_FACTOR)  # Up to 15% more prime
            result['reason'] = f'Long travel distance ({xy_distance:.1f}mm)'
        
        if travel_time > PluginConstants.PRIME_LONG_TIME_THRESHOLD:  # Long travel time
            result['long_travel'] = True
            result['adjustment'] += min(0.1, travel_time / PluginConstants.PRIME_TIME_ADJUSTMENT_FACTOR)  # Up to 10% more prime
            result['reason'] += f', long travel time ({travel_time:.1f}s)'
        
        return result
    
    def _analyzeZChanges(self, prev_section: dict, next_section: dict) -> dict:
        """Analyze Z height changes that might affect priming needs."""
        result = {
            'significant_change': False,
            'adjustment': 0.0,
            'reason': 'Normal Z change',
            'confidence': 'high'
        }
        
        prev_z = prev_section['end_position']['z']
        next_z = next_section['start_position']['z']
        z_change = abs(next_z - prev_z)
        
        # Significant Z changes might indicate pressure changes in the nozzle
        if z_change > PluginConstants.PRIME_LARGE_Z_CHANGE_THRESHOLD:  # More than threshold Z change
            result['significant_change'] = True
            result['adjustment'] = min(0.1, z_change / PluginConstants.PRIME_Z_ADJUSTMENT_FACTOR)  # Up to 10% more prime
            result['reason'] = f'Large Z change ({z_change:.1f}mm)'
        
        return result

    def _generateTransitionWithG92(self, prev_section: dict, next_section: dict, calculated_transitions: list = None) -> list:
        """Generate transition code between sections.
        
        IMPORTANT: Z coordinates are already continuous!
        - Section 1 ends at Z=5.0mm → prev_section['end_position']['z'] = 5.0
        - Section 2 starts at Z=5.0mm → next_section['start_position']['z'] = 5.0
        
        We just need to:
        1. Handle retraction state with intelligent priming
        2. Optionally Z-hop for travel
        3. Move to next XY position
        4. Reset E coordinate (each file starts E from 0)
        
        NO G92 Z needed - Z coordinates already match!
        """
        transition = []
        
        end_state = prev_section['end_position']
        start_state = next_section['start_position'].copy()  # Make a copy so we can modify Z
        
        # CRITICAL FIX: For non-first sections, the nozzle needs to be positioned at the Z height 
        # where the first layer will be printed (transition_z + layer_height), not at the transition_z itself
        if next_section['section_number'] > 1:
            # Get the layer height for this section from calculated transitions
            next_layer_height = 0.2  # Default fallback
            found_transition_data = False
            
            if calculated_transitions:
                # Find the transition data for this section
                for i, trans in enumerate(calculated_transitions):
                    if trans.get('section_num') == next_section['section_number']:
                        found_transition_data = True
                        next_layer_height = trans.get('layer_height', next_layer_height)
                        break
                
                if not found_transition_data:
                    Logger.log("w", f"WARNING: No calculated transition data found for section {next_section['section_number']}, using default layer height {next_layer_height}mm")
            else:
                Logger.log("w", f"WARNING: No calculated_transitions provided, using default layer height {next_layer_height}mm")
            
            # The first layer of this section should be printed at: transition_z + layer_height
            transition_z = start_state['z']
            correct_start_z = transition_z + next_layer_height
            start_state['z'] = correct_start_z
        
        transition.append(";---------- TRANSITION CODE START ----------\n")
        transition.append(f";From Section {prev_section['section_number']} to Section {next_section['section_number']}\n")
        transition.append(f";Previous section ended at: X{end_state['x']:.3f} Y{end_state['y']:.3f} Z{end_state['z']:.3f} E{end_state['e']:.5f}\n")
        transition.append(f";Next section starts at: X{start_state['x']:.3f} Y{start_state['y']:.3f} Z{start_state['z']:.3f} E{start_state['e']:.5f}\n")
        
        # Handle retraction state - we'll prime AFTER travel, store the state for now
        prev_retracted = prev_section['is_retracted_at_end']
        
        # Handle Z-hop and travel moves
        # NOTE: With smart layer alignment, extracted sections include their own Z moves
        # INTELLIGENT FILAMENT STATE MANAGEMENT: Determine if retraction or priming is needed
        filament_decision = self._shouldPrimeForTransition(prev_section, next_section, calculated_transitions)
        
        # Handle retraction BEFORE travel movements (if needed)
        current_e = end_state['e']
        if filament_decision['needs_retract']:
            retract_amount = filament_decision['retract_amount']
            target_e = current_e - retract_amount
            
            # Add retraction before travel
            transition.append(f"; Intelligent retraction: {filament_decision['reason']}\n")
            transition.append(f"; Retract amount: {retract_amount:.3f}mm (confidence: {filament_decision['confidence']})\n")
            transition.append(f"G1 F{filament_decision['retract_speed']} E{target_e:.5f} ; Intelligent retract ({retract_amount:.3f}mm)\n")
            
            # Update current E position after retraction
            current_e = target_e
        
        # So we DON'T set Z here - just handle Z-hop (if enabled) and XY travel
        # Calculate XY distance for more accurate comparison
        xy_distance = ((start_state['x'] - end_state['x'])**2 + (start_state['y'] - end_state['y'])**2)**0.5
        xy_different = xy_distance > 0.001  # 1 micron threshold - always include travel for consistency
        
        # Check if we need to adjust Z height for next section
        z_different = abs(end_state['z'] - start_state['z']) > 0.001
        
        if z_different and self._script_hop_height > 0:
            # Z-hop enabled and Z changes between sections
            # Hop above BOTH the end Z and start Z to avoid collision
            z_hop = max(end_state['z'], start_state['z']) + self._script_hop_height
            transition.append(f"G0 F{self._speed_z_hop} Z{z_hop:.3f} ; Hop up for travel\n")
            # Always include XY travel during Z-hop (even if XY is nearly identical)
            # This ensures consistent gcode and proper positioning
            transition.append(f"G0 F{self._speed_travel} X{start_state['x']:.3f} Y{start_state['y']:.3f} ; Travel to next position\n")
            # Lower to next section's starting Z height
            transition.append(f"G0 F{self._speed_z_hop} Z{start_state['z']:.3f} ; Lower to next section height\n")
        elif z_different:
            # No Z-hop enabled, but Z needs adjustment
            transition.append(f"G0 F{self._speed_z_hop} Z{start_state['z']:.3f} ; Move to next section height\n")
            # Include XY travel if positions differ
            if xy_different:
                transition.append(f"G0 F{self._speed_travel} X{start_state['x']:.3f} Y{start_state['y']:.3f} ; Travel to next position\n")
        elif xy_different:
            # Same Z height: just travel XY (no Z-hop needed for same layer)
            transition.append(f"G0 F{self._speed_travel} X{start_state['x']:.3f} Y{start_state['y']:.3f} ; Travel to next position\n")
        
        # Handle priming AFTER travel movements (if needed)
        if filament_decision['needs_prime']:
            prime_amount = filament_decision['prime_amount']
            target_e = current_e + prime_amount
            
            # Add priming after travel
            transition.append(f"; Intelligent priming: {filament_decision['reason']}\n")
            transition.append(f"; Prime amount: {prime_amount:.3f}mm (confidence: {filament_decision['confidence']})\n")
            transition.append(f"G1 F{filament_decision['prime_speed']} E{target_e:.5f} ; Intelligent prime ({prime_amount:.3f}mm)\n")
            
            # Update current E position after priming
            current_e = target_e
        
        # Document if no filament state change was needed
        if not filament_decision['needs_prime'] and not filament_decision['needs_retract']:
            transition.append(f"; Filament state: {filament_decision['reason']}\n")
        
        # G92 E reset: Set E to the value from the layer BEFORE the next section starts
        # This simulates a natural layer transition as if printing continuously
        # For relative extrusion: reset to 0
        # For absolute extrusion: reset to the E value that would naturally be there
        if self._relative_extrusion:
            transition.append("G92 E0 ; Reset E for next section (relative extrusion)\n")
        else:
            # For absolute: We need the E value from the previous layer of the next section
            # Since trimming already set start_position to the first move's E value,
            # we use that as the baseline. Account for any filament state changes.
            if filament_decision['needs_prime'] or filament_decision['needs_retract']:
                # Filament state was changed, reset to match next section expectation
                transition.append(f"G92 E{start_state['e']:.5f} ; Reset E to match next section (after filament state change)\n")
            else:
                # No filament state change, just reset to match next section
                transition.append(f"G92 E{start_state['e']:.5f} ; Reset E to match next section\n")
        
        transition.append(";---------- TRANSITION CODE END ----------\n\n")
        
        return transition
    
    def _getValue(self, line: str, key: str) -> float:
        """Extract a numeric value for a given key from a gcode line."""
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
