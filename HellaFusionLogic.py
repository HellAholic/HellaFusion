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

from .DisplayCommandService import DisplayCommandService
from .GCodeHeaderService import GCodeHeaderService
from .GCodeParserService import GCodeParserService
from .HellaFusionExceptions import FileProcessingError
from .PluginConstants import PluginConstants
from .TransitionData import TransitionData


class HellaFusionLogic:
    """Core logic for extracting Z height ranges and combining gcode sections."""

    @staticmethod
    def _parseTimeElapsed(line_stripped: str) -> float:
        """Safely parse TIME_ELAPSED value from a comment line.
        
        Handles various formats:
        - ;TIME_ELAPSED:123.456
        - ;TIME_ELAPSED:123.456 ; inline comment
        - ;TIME_ELAPSED: 123.456 (with space after colon)
        
        Args:
            line_stripped: Stripped line that should start with ;TIME_ELAPSED:
            
        Returns:
            Parsed time value, or None if parsing fails
        """
        if not line_stripped.startswith(';TIME_ELAPSED:'):
            return None
        
        try:
            # Remove the prefix ";TIME_ELAPSED:"
            time_str = line_stripped[14:]  # len(";TIME_ELAPSED:") = 14
            
            # Strip any inline comments (in case comment stripping didn't catch it)
            if ';' in time_str:
                time_str = time_str.split(';')[0]
            
            # Parse the float
            return float(time_str.strip())
        except (ValueError, IndexError, AttributeError) as e:
            Logger.log("w", f"Failed to parse TIME_ELAPSED from: '{line_stripped}' - Error: {e}")
            return None

    def __init__(self):
        self._retraction_enabled = True
        self._display_command_service = DisplayCommandService()
        self._header_service = GCodeHeaderService()
        self._parser_service = GCodeParserService()
        self._retraction_retract_speed = 2100
        self._retraction_prime_speed = 2100
        self._relative_extrusion = False
        self._firmware_retraction = False
        self._retraction_amount = 4.5
        self._speed_z_hop = 600
        self._speed_travel = 3000
        self._script_hop_height = 0.4
        self._layer_height = 0.2
        self._shrinkage_compensation_factor = 100.0
        
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
                    
                    # Read layer heights and shrinkage factor from Cura
                    layer_height_raw = float(global_stack.getProperty("layer_height", "value"))
                    initial_layer_height_raw = float(global_stack.getProperty("layer_height_0", "value"))
                    self._shrinkage_compensation_factor = float(global_stack.getProperty("material_shrinkage_percentage_z", "value"))
                    
                    # Convert from Cura format to actual values for plugin calculations
                    # Handle potential import timing issues during module initialization
                    try:
                        self._layer_height = TransitionData.convert_from_cura(layer_height_raw, self._shrinkage_compensation_factor)
                        self._initial_layer_height = TransitionData.convert_from_cura(initial_layer_height_raw, self._shrinkage_compensation_factor)
                    except AttributeError:
                        self._layer_height = layer_height_raw
                        self._initial_layer_height = initial_layer_height_raw
                    
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
    
    def validateTransitions(self, calculated_transitions: list, model_height: float = None) -> dict:
        """Pre-flight validation of transitions before slicing.
        
        Validates:
        - All sections have TransitionData objects
        - Transitions are within model bounds (if model_height provided)
        - No gaps or overlaps between sections
        - Profile compatibility (layer heights are reasonable)
        
        Args:
            calculated_transitions: List of dicts with '_transition_data' from TransitionCalculator
            model_height: Optional model height for bounds checking
            
        Returns:
            dict with 'valid': bool, 'errors': list, 'warnings': list
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            if not calculated_transitions or len(calculated_transitions) == 0:
                result['valid'] = False
                result['errors'].append("No transitions provided")
                return result
            
            # Extract TransitionData objects
            transition_data_list = []
            for i, section_dict in enumerate(calculated_transitions):
                td = section_dict.get('_transition_data')
                if td is None:
                    result['valid'] = False
                    result['errors'].append(f"Section {i}: Missing TransitionData object")
                    continue
                if not isinstance(td, TransitionData):
                    result['valid'] = False
                    result['errors'].append(f"Section {i}: Invalid TransitionData type (got {type(td)})")
                    continue
                transition_data_list.append(td)
            
            if not transition_data_list:
                result['valid'] = False
                result['errors'].append("No valid TransitionData objects found")
                return result
            
            # Validate continuity between sections
            for i in range(len(transition_data_list) - 1):
                current_td = transition_data_list[i]
                next_td = transition_data_list[i + 1]
                
                # Check for gaps
                if current_td.actual_end_z is not None:
                    gap = next_td.actual_start_z - current_td.actual_end_z
                    if abs(gap) > 0.01:  # Allow 0.01mm tolerance
                        if gap > 0:
                            result['warnings'].append(
                                f"Section {i}→{i+1}: Gap of {gap:.3f}mm detected "
                                f"(Section {i} ends at {current_td.actual_end_z:.3f}mm, "
                                f"Section {i+1} starts at {next_td.actual_start_z:.3f}mm)"
                            )
                        else:
                            result['warnings'].append(
                                f"Section {i}→{i+1}: Overlap of {abs(gap):.3f}mm detected "
                                f"(Section {i} ends at {current_td.actual_end_z:.3f}mm, "
                                f"Section {i+1} starts at {next_td.actual_start_z:.3f}mm)"
                            )
            
            # Validate against model height if provided
            if model_height is not None and model_height > 0:
                last_td = transition_data_list[-1]
                if last_td.actual_end_z is not None and last_td.actual_end_z > model_height:
                    result['warnings'].append(
                        f"Last section ends at {last_td.actual_end_z:.3f}mm but model height is {model_height:.3f}mm"
                    )
                
                # Check if first section starts at 0
                first_td = transition_data_list[0]
                if first_td.actual_start_z > 0.01:  # Allow small tolerance
                    result['warnings'].append(
                        f"First section starts at {first_td.actual_start_z:.3f}mm instead of 0mm"
                    )
            
            # Validate layer heights are reasonable
            for i, td in enumerate(transition_data_list):
                if td.layer_height < 0.05 or td.layer_height > 0.5:
                    result['warnings'].append(
                        f"Section {i}: Unusual layer height {td.layer_height:.3f}mm "
                        f"(profile: {td.profile_name})"
                    )
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Validation exception: {str(e)}")
        
        return result
    
    def combineGcodeFiles(self, sections_data: list, output_path: str, calculated_transitions: list = None, expert_settings_enabled: bool = False) -> bool:
        """Combine multiple gcode files into a single spliced file using TransitionData
        
        Args:
            sections_data: List of dicts with 'section_number', 'gcode_file', 'start_height', 'end_height'
            output_path: Path where the combined gcode will be saved
            calculated_transitions: REQUIRED - List of dicts from Controller containing '_transition_data' 
                                   (TransitionData objects from TransitionCalculator)
            expert_settings_enabled: Whether expert settings (like nozzle height G92) are enabled
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            ValueError: If calculated_transitions is missing or doesn't contain TransitionData objects
        """
        # Store expert settings flag for use in transition generation
        self._expert_settings_enabled = expert_settings_enabled
        try:
            # Pre-flight validation
            if calculated_transitions:
                validation_result = self.validateTransitions(calculated_transitions)
                
                # Log warnings
                for warning in validation_result['warnings']:
                    Logger.log("w", f"Validation Warning: {warning}")
                
                # Fail on errors
                if not validation_result['valid']:
                    for error in validation_result['errors']:
                        Logger.log("e", f"Validation Error: {error}")
                    Logger.log("e", "Pre-flight validation failed. Cannot proceed with splicing.")
                    return False
                
                if validation_result['warnings']:
                    Logger.log("i", f"Pre-flight validation passed with {len(validation_result['warnings'])} warning(s)")
                else:
                    Logger.log("i", "Pre-flight validation passed successfully")
            
            # Read all gcode files
            sections = []
            skipped_sections = []
            
            for section_info in sections_data:
                gcode_lines = self._parser_service.readGcodeFile(section_info['gcode_file'])
                if not gcode_lines:
                    Logger.log("e", f"Cannot read G-code file for section {section_info['section_number']}: {section_info['gcode_file']}")
                    Logger.log("e", "Please ensure the slicing process completed successfully and the file exists.")
                    return False
                
                # Extract section data
                section_data = self._extractSectionData(
                    gcode_lines,
                    section_info['section_number'],
                    section_info['start_height'],
                    section_info['end_height'],
                    section_info.get('layer_height', 0.2),  # Use layer_height from Cura profile
                    section_info.get('profile_retraction_settings'),  # Pass retraction settings from profile
                    section_info.get('adjusted_initial'),  # Pass adjusted initial layer height (for trimming)
                    section_info.get('original_initial')  # Pass original initial layer height
                )
                
                if not section_data:
                    Logger.log("e", f"Failed to process section {section_info['section_number']}")
                    Logger.log("e", "This may indicate a problem with the G-code format or slicing settings.")
                    return False
                
                # Add nozzle height from section_info if available
                if 'nozzle_height' in section_info:
                    section_data['nozzle_height'] = section_info['nozzle_height']
                
                # Check if section has valid gcode (not empty, has actual print moves)
                if not section_data['gcode_lines'] or len(section_data['gcode_lines']) < 5:
                    Logger.log("w", f"Section {section_info['section_number']} is empty - transition height {section_info['start_height']:.2f}mm may exceed model height.")
                    Logger.log("w", "Consider reducing the number of sections or adjusting transition heights.")
                    skipped_sections.append(section_info['section_number'])
                    continue
                
                sections.append(section_data)
            
            # Check if we have any valid sections
            if not sections:
                Logger.log("e", "No valid sections found for splicing.")
                Logger.log("e", "All transition heights exceed the model height. Please reduce the number of sections or adjust transition heights.")
                return False
            
            if skipped_sections:
                Logger.log("i", f"Skipped empty section(s): {skipped_sections} (transition heights exceed model height)")
            
            # Pass first gcode file for header extraction
            first_gcode_file = sections_data[0]['gcode_file'] if sections_data else None
            
            # Combine sections using UNIFIED approach
            combined_gcode = self._combineSections(sections, first_gcode_file, calculated_transitions)
            
            if not combined_gcode:
                Logger.log("e", "Failed to combine sections into spliced G-code.")
                Logger.log("e", "This may indicate an issue with transition calculations or G-code processing.")
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
            Logger.log("e", f"Error combining gcode files: {str(e)}")
            raise FileProcessingError(f"Failed to combine gcode files: {str(e)}", operation="combining gcode")
    

    def _extractSectionData(self, gcode_lines: list, section_number: int, start_height: float, end_height: float, layer_height: float = 0.2, retraction_settings: dict = None, adjusted_initial: float = None, original_initial: float = None) -> dict:
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
                'initial_layer_height': adjusted_initial if adjusted_initial is not None else (original_initial if original_initial is not None else layer_height),  # Temp file was sliced with this adjusted value
                'is_retracted_at_start': retraction_enabled,  # Retracted at start if profile has retraction enabled
                'is_retracted_at_end': retraction_enabled,    # Retracted at end if profile has retraction enabled
                'profile_retraction_settings': retraction_settings,
                'nozzle_height': 0.0  # Will be set from section_info if available
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
                # Strip inline comments (keep full comment lines intact)
                if not line_stripped.startswith(";") and ";" in line_stripped:
                    line_stripped = line_stripped.split(";")[0].strip()
                
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
                    if ' X' in line_stripped and self._parser_service.getValue(line_stripped, 'X') is not None:
                        current_x = self._parser_service.getValue(line_stripped, 'X')
                    if ' Y' in line_stripped and self._parser_service.getValue(line_stripped, 'Y') is not None:
                        current_y = self._parser_service.getValue(line_stripped, 'Y')
                    if ' E' in line_stripped and self._parser_service.getValue(line_stripped, 'E') is not None:
                        current_e = self._parser_service.getValue(line_stripped, 'E')
                    
                    # For Section 1 ONLY, collect startup commands
                    if section_number == 1 and start_height == 0:
                        section_data['gcode_lines'].append(line if line.endswith('\n') else line + '\n')
                    
                    continue  # Skip to next line
                
                # Track position changes
                if ' Z' in line_stripped and self._parser_service.getValue(line_stripped, 'Z') is not None:
                    new_z = self._parser_service.getValue(line_stripped, 'Z')
                    prev_z = current_z
                    current_z = new_z
                    # Buffer this Z move - we may need to include it when starting a section
                    last_z_move_line = line if line.endswith('\n') else line + '\n'
                    
                    # Track minimum Z in current layer (to ignore Z-hops)
                    if past_startup:
                        if min_z_in_layer is None or new_z < min_z_in_layer:
                            min_z_in_layer = new_z
                
                if ' X' in line_stripped and self._parser_service.getValue(line_stripped, 'X') is not None:
                    current_x = self._parser_service.getValue(line_stripped, 'X')
                if ' Y' in line_stripped and self._parser_service.getValue(line_stripped, 'Y') is not None:
                    current_y = self._parser_service.getValue(line_stripped, 'Y')
                
                # Track E and retraction state
                if ' E' in line_stripped and self._parser_service.getValue(line_stripped, 'E') is not None:
                    e_val = self._parser_service.getValue(line_stripped, 'E')
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
                
                # Start extraction after startup (after first ;LAYER: marker)
                if not in_section and past_startup and ';LAYER:' in line_stripped:
                    in_section = True
                    section_data['start_position'] = {
                        'x': current_x, 'y': current_y, 'z': current_layer_z, 'e': current_e
                    }
                    # Retraction state now determined from profile settings, not G-code analysis
                    # section_data['is_retracted_at_start'] = is_retracted
                
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
            Logger.log("e", f"Error extracting section data: {str(e)}")
            return None
    
    def _trimSectionToZ(self, section: dict, min_z: float = None, max_z: float = None, transition_data: TransitionData = None) -> dict:
        """Trim section to only include layers within Z range [min_z, max_z].
        
        CRITICAL: The temp G-code file was sliced with the ADJUSTED initial layer height calculated
        by TransitionCalculator. We MUST use TransitionData's adjusted_initial_layer_height and 
        layer_height to calculate which layer numbers exist in THIS section's temp file.
        
        Calculate start layer number and end layer number of each section 
        based on the transition heights of that section, its initial layer height that has been 
        calculated and its layer height.
        
        Args:
            section: Section data dict with gcode_lines
            min_z: Minimum layer Z to include (actual_start_z from TransitionData)
            max_z: Maximum layer Z to include (actual_end_z from TransitionData)
            transition_data: TransitionData object containing adjusted_initial_layer_height and layer_height
        
        Returns new section dict with trimmed gcode_lines and updated positions.
        """
        
        # Use TransitionData values if provided (preferred), fallback to section data
        if transition_data:
            layer_height = transition_data.layer_height
            initial_layer_height = transition_data.adjusted_initial_layer_height
        else:
            # Fallback for backward compatibility
            # NOTE: section data should already contain actual values (converted from Cura format)
            # Do NOT apply shrinkage conversion here - it's already been done when reading from Cura
            layer_height = section.get('layer_height', 0.2)
            initial_layer_height = section.get('initial_layer_height', layer_height)
        
        # Calculate which LAYER NUMBERS to include based on global Z boundaries
        # CRITICAL: Use adjusted initial layer height because that's what the temp file was sliced with!
        # TransitionCalculator calculated this adjusted value for perfect modulo alignment.
        # Formula: layer_num = (z - initial_layer_height) / layer_height
        # This gives us the ;LAYER:N marker number to look for in the temp G-code file
        start_layer_num = 0
        end_layer_num = None  # None means no limit
        
        if max_z is not None:
            # Use round() to handle floating-point precision
            end_layer_num = round((max_z - initial_layer_height) / layer_height)
        
        if min_z is not None:
            # Calculate which layer is AT the transition Z
            # Use round() instead of int() to handle floating-point precision
            transition_layer = round((min_z - initial_layer_height) / layer_height)
            start_layer_num = transition_layer + 1
        
        trimmed_lines = []
        in_valid_layer = False
        startup_done = False
        pending_layer_marker = None
        current_layer_num = -1  # Track current layer number
        
        # Track reference layer (the layer BEFORE start_layer_num for XYE extraction)
        reference_layer_num = None
        reference_layer_lines = []
        in_reference_layer = False
        reference_x_was_extracted = False  # Track if we successfully extracted X from reference layer
        reference_y_was_extracted = False  # Track if we successfully extracted Y from reference layer
        reference_e_was_extracted = False  # Track if we successfully extracted E from reference layer
        if min_z is not None and start_layer_num > 0:
            # The layer before start_layer_num should be extracted for XYE continuity
            reference_layer_num = start_layer_num - 1
        
        # For section 1 (min_z = None), include startup
        # For sections 2+ (min_z set), skip startup entirely
        include_startup = (min_z is None)
        
        for line in section['gcode_lines']:
            line_stripped = line.strip()
            # Strip inline comments (keep full comment lines intact)
            if not line_stripped.startswith(";") and ";" in line_stripped:
                line_stripped = line_stripped.split(";")[0].strip()
            
            # Handle startup (before first ;LAYER:)
            if not startup_done:
                if ';LAYER:' in line_stripped:
                    startup_done = True
                    # CRITICAL FIX: Parse actual layer number from ;LAYER:N marker
                    layer_match = re.search(r';LAYER:(\d+)', line_stripped)
                    if layer_match:
                        current_layer_num = int(layer_match.group(1))
                    else:
                        current_layer_num = 0  # Fallback
                    pending_layer_marker = line
                    
                    # Determine if this layer should be included
                    in_valid_layer = (current_layer_num >= start_layer_num and 
                                     (end_layer_num is None or current_layer_num <= end_layer_num))
                    
                    # Check if this is the reference layer
                    if reference_layer_num is not None and current_layer_num == reference_layer_num:
                        in_reference_layer = True
                        in_valid_layer = False  # Don't include, only extract
                elif include_startup:
                    trimmed_lines.append(line)
                continue
            
            # New layer marker
            if ';LAYER:' in line_stripped:
                # Process any pending reference layer
                if in_reference_layer and reference_layer_lines:
                    extracted = self._extractReferenceFromLayer(section, reference_layer_lines, None)
                    if extracted['x'] is not None:
                        reference_x_was_extracted = True
                    if extracted['y'] is not None:
                        reference_y_was_extracted = True
                    if extracted['e'] is not None:
                        reference_e_was_extracted = True
                    reference_layer_lines = []
                    in_reference_layer = False
                
                # Add previous pending layer if it was valid
                if pending_layer_marker and in_valid_layer:
                    trimmed_lines.append(pending_layer_marker)
                
                # CRITICAL FIX: Parse actual layer number from ;LAYER:N marker, don't just increment
                layer_match = re.search(r';LAYER:(\d+)', line_stripped)
                if layer_match:
                    current_layer_num = int(layer_match.group(1))
                else:
                    current_layer_num += 1  # Fallback: increment if parsing fails
                pending_layer_marker = line
                
                # Determine if this NEW layer should be included
                in_valid_layer = (current_layer_num >= start_layer_num and 
                                 (end_layer_num is None or current_layer_num <= end_layer_num))
                
                # Check if this is the reference layer
                if reference_layer_num is not None and current_layer_num == reference_layer_num:
                    in_reference_layer = True
                    in_valid_layer = False  # Don't include, only extract                

                # Check if we've passed the end boundary
                if end_layer_num is not None and current_layer_num > end_layer_num:
                    # We're past the end, stop processing
                    break
                
                continue
            
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
            'reference_layer_time': section.get('reference_layer_time'),  # Preserve TIME_ELAPSED from reference layer for time delta calculation!
            'nozzle_height': section.get('nozzle_height', 0.0),
            'gcode_lines': trimmed_lines
        }
        
        # Update end/start positions based on actual trim points
        if max_z is not None:
            trimmed_section['end_position']['z'] = max_z
        if min_z is not None:
            trimmed_section['start_position']['z'] = min_z

        # Scan for actual XYE positions at START boundary
        # Only update values that were NOT extracted from reference layer
        # Reference layer values (from previous layer) are what we need for proper transition
        if min_z is not None:
            for line in trimmed_lines:
                line_stripped = line.strip()
                # Strip inline comments (keep full comment lines intact)
                if not line_stripped.startswith(";") and ";" in line_stripped:
                    line_stripped = line_stripped.split(";")[0].strip()
                if line_stripped.startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
                    match_x = re.search(r' X(\d+\.?\d*)', line_stripped)
                    match_y = re.search(r' Y(\d+\.?\d*)', line_stripped)
                    match_e = re.search(r' E(-?\d+\.?\d*)', line_stripped)
                    
                    if match_x and not reference_x_was_extracted:
                        trimmed_section['start_position']['x'] = float(match_x.group(1))
                    if match_y and not reference_y_was_extracted:
                        trimmed_section['start_position']['y'] = float(match_y.group(1))
                    if match_e and not reference_e_was_extracted:
                        trimmed_section['start_position']['e'] = float(match_e.group(1))
                    
                    # Found first G0/G1 with coordinates, stop scanning
                    if match_x or match_y or match_e:
                        break
        
        # Scan for actual XYE positions at END boundary (scan backwards)
        # Track both last E value (might be retracted) and last extrusion E (unretracted)
        last_e_value = None
        last_extrusion_e = None
        prev_e = None
        found_x = False
        found_y = False
        found_e = False
        
        for line in reversed(trimmed_lines):
            if line.strip().startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
                match_x = re.search(r' X(\d+\.?\d*)', line)
                match_y = re.search(r' Y(\d+\.?\d*)', line)
                match_e = re.search(r' E(-?\d+\.?\d*)', line)
                
                if match_x and not found_x:
                    trimmed_section['end_position']['x'] = float(match_x.group(1))
                    found_x = True
                if match_y and not found_y:
                    trimmed_section['end_position']['y'] = float(match_y.group(1))
                    found_y = True
                if match_e:
                    current_e = float(match_e.group(1))
                    if not found_e:
                        last_e_value = current_e
                        trimmed_section['end_position']['e'] = current_e
                        found_e = True
                    
                    # Detect if this is an extrusion (E increasing) vs retraction (E decreasing)
                    if prev_e is not None:
                        if current_e > prev_e:  # Extrusion move (E increasing)
                            if last_extrusion_e is None:
                                last_extrusion_e = current_e
                    prev_e = current_e
                
                # Stop after we've found all three values (X, Y, and E)
                if found_x and found_y and found_e:
                    break
        
        # Store the unretracted E position for transition comments
        if last_extrusion_e is not None:
            trimmed_section['unretracted_e'] = last_extrusion_e
        else:
            # Fallback: use the last E value if no extrusion found
            trimmed_section['unretracted_e'] = last_e_value if last_e_value is not None else 0.0
        
        return trimmed_section
    
    def _extractReferenceFromLayer(self, section: dict, reference_layer_lines: list, reference_z: float = None) -> dict:
        """Extract XYE values from the reference layer lines and update section's start_position.
        
        This method processes the reference layer (that will be excluded from output) to get
        the final XYE position that should be used for the transition.
        
        Args:
            section: Section data dict to update with reference values
            reference_layer_lines: List of gcode lines from the reference layer
            reference_z: Z height of the reference layer (optional, can be None)
            
        Returns:
            Dict with extracted values: {'x': float, 'y': float, 'e': float} or None for each
        """
        
        # Extract the final XYE values from the reference layer
        final_x = None
        final_y = None
        final_e = None
        
        # Scan through the reference layer lines to find the last XYE values
        for line in reference_layer_lines:
            line_stripped = line.strip()
            # Strip inline comments (keep full comment lines intact)
            if not line_stripped.startswith(";") and ";" in line_stripped:
                line_stripped = line_stripped.split(";")[0].strip()
            
            if line_stripped.startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
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
        
        # Set the Z to the reference layer's Z height if provided
        if reference_z is not None:
            section['start_position']['z'] = reference_z
        
        return {'x': final_x, 'y': final_y, 'e': final_e}
    
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
        
        # Find the layer that matches target_z (this will be the first layer after trimming)
        target_layer_num = None
        prev_layer_num = None
        current_layer_num = None
        layer_z_map = {}  # Map layer numbers to their Z heights
        
        # Build a map of layer numbers to Z heights
        for line in section['gcode_lines']:
            line_stripped = line.strip()
            # Strip inline comments (keep full comment lines intact)
            if not line_stripped.startswith(";") and ";" in line_stripped:
                line_stripped = line_stripped.split(";")[0].strip()
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
            Logger.log("w", f"Could not find target layer at Z={target_z:.3f}mm for reference time extraction")
            # Still try to extract reference time from first available layer
            if layer_z_map:
                # Use the first layer as fallback
                target_layer_num = min(layer_z_map.keys())
            else:
                return section
        
        # We want XYE values AND TIME_ELAPSED from the END of the reference layer
        # Extract both in a single pass through the G-code
        prev_layer_num = target_layer_num
        prev_layer_x = None
        prev_layer_y = None
        prev_layer_e = None
        reference_layer_time = None
        in_prev_layer = False
        
        for line in section['gcode_lines']:  # Scan the current gcode_lines
            line_stripped = line.strip()
            # Strip inline comments (keep full comment lines intact)
            if not line_stripped.startswith(";") and ";" in line_stripped:
                line_stripped = line_stripped.split(";")[0].strip()
            
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
            
            # While in the reference layer, collect LAST XYE and TIME_ELAPSED
            if in_prev_layer:
                # Collect XYE from G0/G1 commands
                if line_stripped.startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
                    match_x = re.search(r' X(\d+\.?\d*)', line_stripped)
                    match_y = re.search(r' Y(\d+\.?\d*)', line_stripped)
                    match_e = re.search(r' E(-?\d+\.?\d*)', line_stripped)
                    
                    if match_x:
                        prev_layer_x = float(match_x.group(1))
                    if match_y:
                        prev_layer_y = float(match_y.group(1))
                    if match_e:
                        prev_layer_e = float(match_e.group(1))
                
                # Collect TIME_ELAPSED (keep last one found in layer)
                elif line_stripped.startswith(';TIME_ELAPSED:'):
                    parsed_time = self._parseTimeElapsed(line_stripped)
                    if parsed_time is not None:
                        reference_layer_time = parsed_time
        
        # If we didn't find an E value (empty layer with only travel moves), look at the previous layer
        if prev_layer_e is None and prev_layer_num > 0:
            prev_layer_num = prev_layer_num - 1
            in_prev_layer = False
            reference_layer_time = None  # Reset time, need to extract from the fallback layer
            
            for line in section['gcode_lines']:
                line_stripped = line.strip()
                # Strip inline comments (keep full comment lines intact)
                if not line_stripped.startswith(";") and ";" in line_stripped:
                    line_stripped = line_stripped.split(";")[0].strip()
                
                if ';LAYER:' in line_stripped:
                    layer_match = re.search(r';LAYER:(\d+)', line_stripped)
                    if layer_match:
                        layer_num = int(layer_match.group(1))
                        if layer_num == prev_layer_num:
                            in_prev_layer = True
                        elif in_prev_layer and layer_num > prev_layer_num:
                            break
                
                if in_prev_layer:
                    # Collect XYE
                    if line_stripped.startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
                        match_x = re.search(r' X(\d+\.?\d*)', line_stripped)
                        match_y = re.search(r' Y(\d+\.?\d*)', line_stripped)
                        match_e = re.search(r' E(-?\d+\.?\d*)', line_stripped)
                        
                        if match_x:
                            prev_layer_x = float(match_x.group(1))
                        if match_y:
                            prev_layer_y = float(match_y.group(1))
                        if match_e:
                            prev_layer_e = float(match_e.group(1))
                    
                    # Collect TIME_ELAPSED
                    elif line_stripped.startswith(';TIME_ELAPSED:'):
                        parsed_time = self._parseTimeElapsed(line_stripped)
                        if parsed_time is not None:
                            reference_layer_time = parsed_time
        
        # Store reference layer time for time adjustment algorithm
        if reference_layer_time is not None:
            section['reference_layer_time'] = reference_layer_time
        else:
            Logger.log("w", f"Section {section.get('section_number', '?')}: Could not extract reference layer time from layer {prev_layer_num} at target_z={target_z:.3f}mm")
        
        # Update start_position
        if prev_layer_x is not None:
            section['start_position']['x'] = prev_layer_x
        if prev_layer_y is not None:
            section['start_position']['y'] = prev_layer_y
        if prev_layer_e is not None:
            section['start_position']['e'] = prev_layer_e
        
        return section
    
    def _combineSections(self, sections: list, first_gcode_file: str = None, calculated_transitions: list = None) -> list:
        """Combine sections using TransitionData objects.
        
        This method extracts TransitionData objects from calculated_transitions and uses
        their pre-calculated boundaries directly. No more searching, no fallbacks.
        
        TransitionCalculator has already:
        1. Determined EXACT Z coordinates where transitions occur (actual_start_z, actual_end_z)
        2. Calculated perfect initial layer height adjustments for gap-free transitions
        3. Used iterative pattern matching where each section becomes the base pattern for the next
        4. Validated all transitions for continuity
        
        Args:
            sections: List of section data dicts from gcode extraction
            first_gcode_file: Path to first gcode file to extract header from
            calculated_transitions: REQUIRED - List of dicts containing '_transition_data' 
                                   (TransitionData objects from TransitionCalculator)
                                   
        Raises:
            ValueError: If TransitionData objects are missing from calculated_transitions
        """
        try:
            combined = []
            
            # Add header from first file ONLY
            if first_gcode_file:
                first_gcode = self._parser_service.readGcodeFile(first_gcode_file)
                if first_gcode:
                    in_header = False
                    for line in first_gcode:
                        line_stripped = line.strip()
                        # Strip inline comments (keep full comment lines intact)
                        if not line_stripped.startswith(";") and ";" in line_stripped:
                            line_stripped = line_stripped.split(";")[0].strip()
                        
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

            alignment_points = []
            transition_data_objects = []
            
            # Extract TransitionData objects from sections
            for i, section_dict in enumerate(calculated_transitions):
                td = section_dict.get('_transition_data')
                if td is None:
                    raise ValueError(f"Section {i}: Missing _transition_data object.")
                if not isinstance(td, TransitionData):
                    raise ValueError(f"Section {i}: _transition_data is not a TransitionData object (got {type(td)})")
                transition_data_objects.append(td)
            
            # Build alignment points from TransitionData objects
            # For N sections, we have N-1 transition boundaries
            for i in range(len(transition_data_objects) - 1):
                current_td = transition_data_objects[i]
                next_td = transition_data_objects[i + 1]
                
                # Use EXACT calculated boundaries from TransitionCalculator
                # Current section ends at its actual_end_z
                end_z_a = current_td.actual_end_z
                # Next section starts at its actual_start_z (should match end_z_a for continuity)
                start_z_b = next_td.actual_start_z
                
                alignment_points.append((i, end_z_a, start_z_b))
            
            # Use actual_start_z/actual_end_z from TransitionData (calculated boundaries)
            # NOT user-specified boundaries! Each section must be trimmed based on ITS OWN parameters.
            trim_boundaries = {}
            for i in range(len(sections)):
                td = transition_data_objects[i]
                # For each section, use the CALCULATED boundaries from TransitionData
                # actual_start_z = where this section ACTUALLY starts (after adjustment)
                # actual_end_z = where this section ACTUALLY ends (None for last section = top)
                trim_boundaries[i] = {
                    'min_z': td.actual_start_z if i > 0 else None,  # First section starts from 0, no trimming needed
                    'max_z': td.actual_end_z,  # Can be None for last section
                    'transition_data': td  # Pass TransitionData object for layer calculations
                }
            
            # For sections 2+, extract XYE values from previous layer BEFORE trimming
            # The previous layer is still in the original section at this point
            for i in range(1, len(sections)):
                start_z_for_this_section = trim_boundaries[i]['min_z']
                if start_z_for_this_section is not None:
                    sections[i] = self._extractPreviousLayerValues(sections[i], start_z_for_this_section)
            
            # Now do the actual trimming - ONCE per section with TransitionData
            for i in range(len(sections)):
                td = trim_boundaries[i]['transition_data']
                min_z = trim_boundaries[i]['min_z']
                max_z = trim_boundaries[i]['max_z']
                
                # Only trim if there are actual boundaries set
                if min_z is not None or max_z is not None:
                    sections[i] = self._trimSectionToZ(sections[i], min_z, max_z, td)
            
            # Count total layers AFTER trimming
            current_layer = 0
            total_layers = 0
            for section in sections:
                layer_count = 0
                for line in section['gcode_lines']:
                    if line.strip().startswith(';LAYER:'):
                        layer_count += 1
                total_layers += layer_count
            
            # Calculate time deltas for each section transition
            # Section 1 has no delta (time_delta = 0.0)
            # For sections 2+: delta = (ADJUSTED last TIME_ELAPSED of prev section) - (reference_layer_time of current section)
            # CRITICAL: We must use the ADJUSTED end time from previous section, not the original unadjusted time!
            sections[0]['time_delta'] = 0.0  # First section keeps original times
            
            for i in range(1, len(sections)):
                # Find last TIME_ELAPSED from previous section (UNADJUSTED)
                prev_section_last_time_unadjusted = None
                for line in reversed(sections[i-1]['gcode_lines']):
                    line_stripped = line.strip()
                    if line_stripped.startswith(';TIME_ELAPSED:'):
                        parsed_time = self._parseTimeElapsed(line_stripped)
                        if parsed_time is not None:
                            prev_section_last_time_unadjusted = parsed_time
                            break
                
                # Calculate the ADJUSTED end time of previous section
                # Adjusted time = original time + previous section's delta
                prev_section_delta = sections[i-1].get('time_delta', 0.0)
                baseline_time_section_a = None
                if prev_section_last_time_unadjusted is not None:
                    baseline_time_section_a = prev_section_last_time_unadjusted + prev_section_delta
                
                # Get reference layer time from current section
                baseline_time_section_b = sections[i].get('reference_layer_time', None)
                
                # Calculate delta with detailed logging
                if baseline_time_section_a is not None and baseline_time_section_b is not None:
                    time_delta = baseline_time_section_a - baseline_time_section_b
                    sections[i]['time_delta'] = time_delta
                    
                    # Log detailed calculation for debugging
                    Logger.log("d", f"Section {sections[i]['section_number']} time delta: {time_delta:.3f}s "
                             f"(prev_end={baseline_time_section_a:.3f}s, curr_ref={baseline_time_section_b:.3f}s)")
                elif baseline_time_section_a is None:
                    sections[i]['time_delta'] = 0.0
                    Logger.log("e", f"Section {sections[i]['section_number']}: Could not find TIME_ELAPSED from previous section - using delta=0. "
                             f"Time estimates will be INCORRECT!")
                else:  # baseline_time_section_b is None
                    sections[i]['time_delta'] = 0.0
                    Logger.log("e", f"Section {sections[i]['section_number']}: Missing reference_layer_time - using delta=0. "
                             f"Time estimates will be INCORRECT! Check that trimming preserved the correct layers.")
            
            # Validate time deltas and log summary
            invalid_deltas = sum(1 for sec in sections[1:] if sec.get('time_delta', 0.0) == 0.0 and sec.get('reference_layer_time') is None)
            if invalid_deltas > 0:
                Logger.log("w", f"WARNING: {invalid_deltas} section(s) have invalid time deltas. Final time estimate may be incorrect.")
            else:
                Logger.log("i", f"Time delta calculation completed successfully for all {len(sections)} section(s)")
            
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
                time_delta = section.get('time_delta', 0.0)  # Get pre-calculated time delta for this section
                time_adjusted_count = 0  # Count how many times we adjust
                
                for line in section['gcode_lines']:
                    line_stripped = line.strip()
                    # Strip inline comments (keep full comment lines intact)
                    if not line_stripped.startswith(";") and ";" in line_stripped:
                        line_stripped = line_stripped.split(";")[0].strip()
                    
                    # Renumber LAYER_COUNT in startup section
                    if line_stripped.startswith(';LAYER_COUNT:'):
                        combined.append(f";LAYER_COUNT:{total_layers}\n")
                        continue
                    
                    # Renumber layer markers
                    if line_stripped.startswith(';LAYER:'):
                        combined.append(f";LAYER:{current_layer}\n")
                        current_layer += 1
                        continue
                    
                    # Update TIME_ELAPSED comments using pre-calculated delta
                    if line_stripped.startswith(';TIME_ELAPSED:'):
                        original_time = self._parseTimeElapsed(line_stripped)
                        if original_time is not None:
                            # Apply the time delta to adjust for section transitions
                            adjusted_time = original_time + time_delta
                            combined.append(f";TIME_ELAPSED:{adjusted_time:.6f}\n")
                            time_adjusted_count += 1
                            continue
                        else:
                            # If parsing fails, keep original line
                            Logger.log("w", f"Failed to parse TIME_ELAPSED: {line_stripped}")
                            # Fall through to append original line
                    
                    # For sections 2+, DON'T strip Z - the extracted section includes the Z move for proper positioning
                    # The transition will handle XY/E, but Z positioning is from the extracted section
                    # (This changed when we implemented smart layer alignment)
                    
                    # Mark that we've passed the first move
                    if line_stripped.startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
                        first_move_in_section = False
                    
                    # Copy all other lines as-is
                    combined.append(line if line.endswith('\n') else line + '\n')
                
                combined.append(f";========== SECTION {section['section_number']} END ==========\n\n")
            
            # Update header TIME value to match final TIME_ELAPSED
            combined = self._header_service.updateHeaderTime(combined)
            
            # Update M117/M118 LCD display commands (if present)
            combined = self._display_command_service.updateDisplayCommands(combined)
            
            return combined
            
        except Exception as e:
            Logger.log("e", f"Error combining sections: {str(e)}")
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
            # Strip inline comments (keep full comment lines intact)
            if not line_stripped.startswith(";") and ";" in line_stripped:
                line_stripped = line_stripped.split(";")[0].strip()
            
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
                elif line_stripped.startswith(('G0' , 'G1' , 'G2' , 'G3' , 'G92')):
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

    def _formatTransitionComment(self, label: str, x: float, y: float, z: float, e: float) -> str:
        """Format a transition comment line with aligned columns for better readability.
        
        Args:
            label: The comment label (e.g., "Previous section ended at")
            x, y, z: Position coordinates
            e: Extruder value
            
        Returns:
            Formatted comment string with aligned columns
            
        Example output:
            ;Previous section ended at:      X163.996    Y111.336     Z20.000     E428.64499
            ;Next section starts at:         X158.874    Y123.106     Z20.100    E2058.33703
        """
        # Format the label with consistent width (35 characters for alignment)
        label_str = f";{label}:"
        formatted_line = f"{label_str:<35}"
        
        # Format coordinates with right-alignment
        # X, Y, Z: 12 characters each (right-aligned)
        # E: 15 characters (right-aligned, needs more space for large values)
        formatted_line += f"X{x:>10.3f} "
        formatted_line += f"Y{y:>10.3f} "
        formatted_line += f"Z{z:>11.3f} "
        formatted_line += f"E{e:>13.5f}"
        
        return formatted_line + "\n"

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
        
        # Use unretracted E value for comment (more useful for debugging)
        prev_unretracted_e = prev_section.get('unretracted_e', end_state['e'])
        
        # Format transition comments with aligned columns for easy reading
        transition.append(self._formatTransitionComment(
            "Previous section ended at",
            end_state['x'], end_state['y'], end_state['z'], prev_unretracted_e
        ))
        transition.append(self._formatTransitionComment(
            "Next section starts at",
            start_state['x'], start_state['y'], start_state['z'], start_state['e']
        ))
        
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
        
        # Calculate nozzle height delta for G92 Z offset compensation
        prev_nozzle_height = prev_section.get('nozzle_height', 0.0)
        next_nozzle_height = next_section.get('nozzle_height', 0.0)
        delta_nozzle = prev_nozzle_height - next_nozzle_height
        has_nozzle_offset = abs(delta_nozzle) > 0.001  # Meaningful difference threshold
        
        # Helper function to add G92 Z offset if needed
        def add_nozzle_offset(current_z: float) -> None:
            """Add G92 Z command to compensate for nozzle height difference.
            Only adds the command if Expert Settings are enabled in the UI."""
            # Only add G92 Z offset if expert settings are enabled
            if has_nozzle_offset and self._expert_settings_enabled:
                adjusted_z = current_z + delta_nozzle
                transition.append(f"G92 Z{adjusted_z:.3f} ; Adjust Z for nozzle height difference ({delta_nozzle:+.2f}mm)\n")
        
        # Generate movement commands based on the transition type
        if z_different and self._script_hop_height > 0:
            # Case 1: Z-hop enabled with Z height change
            # Hop above BOTH end and start Z to avoid collision during travel
            z_hop = max(end_state['z'], start_state['z']) + self._script_hop_height
            transition.append(f"G0 F{self._speed_z_hop} Z{z_hop:.3f} ; Hop up for travel\n")
            add_nozzle_offset(z_hop)  # Apply nozzle offset at hop height
            transition.append(f"G0 F{self._speed_travel} X{start_state['x']:.3f} Y{start_state['y']:.3f} ; Travel to next position\n")
            transition.append(f"G0 F{self._speed_z_hop} Z{start_state['z']:.3f} ; Lower to next section height\n")
            
        elif z_different:
            # Case 2: Z height change without Z-hop
            add_nozzle_offset(end_state['z'])  # Apply nozzle offset before Z move
            transition.append(f"G0 F{self._speed_z_hop} Z{start_state['z']:.3f} ; Move to next section height\n")
            if xy_different:
                transition.append(f"G0 F{self._speed_travel} X{start_state['x']:.3f} Y{start_state['y']:.3f} ; Travel to next position\n")
                
        elif xy_different:
            # Case 3: Same Z height, only XY travel needed
            add_nozzle_offset(start_state['z'])  # Apply nozzle offset at current height
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
    
