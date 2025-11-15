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

import os
import json
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

from UM.Logger import Logger
from cura.CuraApplication import CuraApplication
from cura.Machines.ContainerTree import ContainerTree
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator


from .ProfileSwitchingService import ProfileSwitchingService
from .HellaFusionExceptions import ProfileSwitchError


class HellaFusionController(QObject):
    """Controller class that handles all business logic for the HellaFusion plugin."""
    
    # Signals
    qualityProfilesLoaded = pyqtSignal(list)  # quality_profiles
    logMessageEmitted = pyqtSignal(str, bool)  # message, is_error
    
    # Settings file path
    SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "hellafusion_settings.json")
    
    def __init__(self):
        super().__init__()
        self._quality_profiles = []
        self._profile_service = ProfileSwitchingService()
        
        # Load quality profiles asynchronously
        self._loadQualityProfilesAsync()
    
    def getQualityProfiles(self):
        """Get the current quality profiles."""
        return self._quality_profiles
    
    def loadSettings(self):
        """Load saved settings from JSON file."""
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r') as f:
                    settings = json.load(f)
                return settings
            else:
                return {}
        except Exception as e:
            Logger.log("w", f"Failed to load HellaFusion settings: {str(e)}")
            return {}
    
    def saveSettings(self, settings):
        """Save current settings to JSON file."""
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            Logger.log("w", f"Failed to save HellaFusion settings: {str(e)}")
    
    def validateStartProcessing(self, dest_folder, transitions):
        """Validate inputs before starting processing."""
        from .HellaFusionExceptions import ValidationError
        
        errors = []
        
        # Check if model exists on build plate
        try:
            application = CuraApplication.getInstance()
            scene = application.getController().getScene()
            nodes = [node for node in DepthFirstIterator(scene.getRoot()) if node.getMeshData()]
            
            if not nodes:
                errors.append("No model on build plate. Please load a model first.")
        except Exception as e:
            Logger.log("e", f"Error checking for model: {e}")
            errors.append("Error checking for model on build plate")
            
        # Validate destination folder
        if not dest_folder:
            errors.append("Please select a destination folder")
        elif not dest_folder.strip():
            errors.append("Destination folder cannot be empty")
        elif not os.path.exists(dest_folder):
            errors.append(f"Destination folder does not exist: {dest_folder}")
        else:
            # Check if folder is writable
            try:
                test_file = os.path.join(dest_folder, "test_write.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                errors.append(f"Cannot write to destination folder: {dest_folder}")
        
        # Validate transitions
        if not transitions:
            errors.append("Please add at least one section")
        else:
            # Validate each transition
            for i, transition in enumerate(transitions):
                section_num = transition.get('section_number', i + 1)
                
                # Check profile selection
                if not transition.get('profile_id'):
                    errors.append(f"Section {section_num}: Please select a quality profile")
                
                # Check transition heights are valid
                start_height = transition.get('start_height', 0)
                end_height = transition.get('end_height')
                
                if end_height is not None:
                    if end_height <= start_height:
                        errors.append(f"Section {section_num}: End height ({end_height}mm) must be greater than start height ({start_height}mm)")
                    
                    if end_height > 1000:  # Reasonable maximum
                        errors.append(f"Section {section_num}: Transition height ({end_height}mm) seems unusually high")
                
                # Check for overlapping transitions
                if i > 0:
                    prev_end = transitions[i-1].get('end_height')
                    if prev_end and start_height < prev_end:
                        errors.append(f"Section {section_num}: Overlapping transition heights detected")
            
        # Check quality profiles availability
        if not self._quality_profiles:
            errors.append("No quality profiles available. Please wait for profiles to load or click 'Reload Profiles'.")
        
        return errors
    
    def normalizeIntentName(self, intent_category):
        """Normalize intent category names for display."""
        if not intent_category or intent_category in ["", "default"]:
            return "Balanced"
        
        intent_mapping = {
            "default": "Balanced",
            "engineering": "Engineering",
            "accurate": "Engineering",
            "draft": "Draft",
            "quick": "Draft",
            "balanced": "Balanced",
            "fast": "Fast", 
            "fine": "Fine",
            "high_quality": "High Quality",
            "smooth": "Smooth",
            "strong": "Strong",
            "visual": "Visual"
        }
        
        return intent_mapping.get(intent_category.lower(), intent_category.title())
    
    def _logMessage(self, message, is_error=False):
        """Emit a log message signal."""
        self.logMessageEmitted.emit(message, is_error)
        if is_error:
            Logger.log("e", message)
    
    def _loadQualityProfilesAsync(self):
        """Load quality profiles asynchronously to avoid blocking the UI."""
        self._logMessage("Loading quality profiles...")
        QTimer.singleShot(100, self._loadQualityProfiles)
    
    def _buildCompatibleDefinitionsList(self, machine_definition_id, global_stack):
        """Build a list of compatible definition IDs using Cura's proper inheritance chain."""
        current_definition = global_stack.definition
        quality_definition = current_definition.getMetaDataEntry("quality_definition", machine_definition_id)
        
        compatible_definitions = [machine_definition_id]
        
        if quality_definition and quality_definition not in compatible_definitions:
            compatible_definitions.append(quality_definition)
        
        try:
            # Use metadata to get inheritance chain
            inherited_from = current_definition.getMetaDataEntry("inherits", "")
            if inherited_from and inherited_from not in compatible_definitions:
                compatible_definitions.append(inherited_from)
        except Exception as ancestor_error:
            Logger.log("w", f"Could not get inheritance chain: {ancestor_error}")
        
        return compatible_definitions

    def _loadQualityProfiles(self):
        """Load available quality profiles using the proper Cura API (from AutoSlicer)."""
        try:
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            
            if not global_stack:
                self._logMessage("No active machine found.", is_error=True)
                return

            machine_name = global_stack.definition.getName()
            machine_definition_id = global_stack.definition.getId()
            
            self._logMessage(f"Detected machine: {machine_name} (ID: {machine_definition_id})")
            
            actual_machine_id = machine_definition_id
            if machine_definition_id == "fdmprinter":
                Logger.log("w", "Machine detected as fdmprinter - looking for specific definition...")
                
                container_registry = application.getContainerRegistry()
                all_machine_definitions = container_registry.findDefinitionContainers(type="machine")
                
                potential_matches = []
                for definition in all_machine_definitions:
                    def_id = definition.getId()
                    def_name = definition.getName().lower()
                    
                    machine_name_words = machine_name.lower().split()
                    if any(word in def_name for word in machine_name_words if len(word) > 2):
                        potential_matches.append((def_id, definition.getName()))
                
                if potential_matches:
                    actual_machine_id = potential_matches[0][0]
                    self._logMessage(f"Found specific machine definition: {potential_matches[0][1]} ({actual_machine_id})")
            
            machine_definition_id = actual_machine_id
            
            self._quality_profiles = []
            
            try:
                container_tree = ContainerTree.getInstance()
                machine_definition_id = global_stack.definition.getId()
                
                machine_node = container_tree.machines[machine_definition_id]
                                
                # Get current machine configuration
                variant_names = [extruder.variant.getName() for extruder in global_stack.extruderList]
                material_bases = [extruder.material.getMetaDataEntry("base_file") for extruder in global_stack.extruderList]
                
                # Collect available quality_types for this machine/variant/material combination
                available_quality_types = set()
                
                # Get the current variant and material nodes for the first extruder (or global)
                current_variant = machine_node.variants.get(variant_names[0]) if variant_names else None
                if current_variant and material_bases[0]:
                    current_material = current_variant.materials.get(material_bases[0])
                    if current_material:
                        # Iterate through all quality nodes for this material to collect available quality_types
                        for quality_node in current_material.qualities.values():
                            available_quality_types.add(quality_node.quality_type)
                            
                            # Check if this quality node has intent profiles
                            if hasattr(quality_node, 'intents') and quality_node.intents:
                                # Process each intent profile for this quality
                                for intent_id, intent_node in quality_node.intents.items():                                    
                                    try:
                                        intent_container = intent_node.container
                                        if not intent_container:
                                            Logger.log("w", f"Intent {intent_id} has no container")
                                            continue
                                            
                                        # Get intent metadata - handle empty_intent as default
                                        if intent_id == "empty_intent":
                                            intent_category = "default"
                                        else:
                                            intent_category = intent_node.intent_category
                                        
                                        # Get the quality name from the base quality container
                                        quality_name = quality_node.container.getName()
                                        quality_type = quality_node.quality_type

                                        # Create a profile entry with the intent-specific information
                                        profile_entry = {
                                            'display_name': f"[M] {quality_name}",
                                            'container': quality_node.container,
                                            'intent': intent_category,
                                            'quality_name': quality_name,
                                            'quality_group': None,
                                            'quality_type': quality_type,
                                            'is_available': True,
                                            'intent_container': intent_container
                                        }
                                        self._quality_profiles.append(profile_entry)
                                        
                                    except Exception as intent_error:
                                        Logger.log("w", f"Error processing intent {intent_id}: {intent_error}")
                            else:
                                # No intents available, add the base quality profile with default intent
                                try:
                                    quality_name = quality_node.container.getName()
                                    quality_type = quality_node.quality_type
                                    
                                    profile_entry = {
                                        'display_name': quality_name,
                                        'container': quality_node.container,
                                        'intent': "default",
                                        'quality_name': quality_name,
                                        'quality_group': None,
                                        'quality_type': quality_type,
                                        'is_available': True
                                    }
                                    self._quality_profiles.append(profile_entry)
                                except Exception as base_error:
                                    Logger.log("w", f"Error adding base quality {quality_node.container_id}: {base_error}")
                    else:
                        Logger.log("w", f"No material node found for base: {material_bases[0]}")
                else:
                    Logger.log("w", f"No variant node found for: {variant_names[0] if variant_names else 'No variant'}")
                                        
            except Exception as tree_error:
                Logger.log("w", f"ContainerTree intent scanning failed: {tree_error}, falling back to container registry")
                available_quality_types = set()  # Initialize empty set for fallback
            
            # Always scan for user-defined quality_changes profiles
            container_registry = application.getContainerRegistry()
            all_quality_changes = container_registry.findInstanceContainers(type="quality_changes")
            quality_changes_containers = []
            
            # Build compatibility list using inheritance chain
            compatible_definitions = self._buildCompatibleDefinitionsList(machine_definition_id, global_stack)
            
            # Add quality_definition if different from machine_definition_id
            current_definition = global_stack.definition
            quality_definition = current_definition.getMetaDataEntry("quality_definition", machine_definition_id)
            if quality_definition and quality_definition not in compatible_definitions:
                compatible_definitions.append(quality_definition)
                        
            for qc_container in all_quality_changes:
                try:
                    qc_name = qc_container.getName()
                    qc_definition = qc_container.getMetaDataEntry("definition", "unknown")
                    qc_position = qc_container.getMetaDataEntry("position")
                    qc_quality_type = qc_container.getMetaDataEntry("quality_type", "normal")
                                        
                    # Skip if this is an extruder-specific container (we want global ones)
                    if qc_position is not None:
                        continue
                        
                    # Enhanced compatibility check using expanded definition list
                    is_compatible = False
                    
                    # Check if the quality_changes definition matches any compatible definition
                    if qc_definition in compatible_definitions:
                        is_compatible = True
                    elif qc_definition == "unknown":
                        is_compatible = True
                    
                    # Check if the quality_type is available for current nozzle/material combination
                    if is_compatible and available_quality_types:
                        if qc_quality_type not in available_quality_types:
                            is_compatible = False
                    
                    if is_compatible:
                        quality_changes_containers.append(qc_container)
                        
                except Exception as qc_error:
                    Logger.log("w", f"Error checking quality_changes compatibility for {qc_container.getId()}: {qc_error}")
                    continue
            
            # Process found user-defined quality changes
            for quality_changes_container in quality_changes_containers:
                try:
                    quality_name = quality_changes_container.getName()
                    intent_category = quality_changes_container.getMetaDataEntry("intent_category", "default")
                    quality_type = quality_changes_container.getMetaDataEntry("quality_type", "normal")
                    
                    # Filter out unwanted profiles
                    if quality_name.lower() in ["empty", "not_supported"] or intent_category == "Not_Supported":
                        continue
                    
                    # Enhanced intent detection for quality changes
                    if intent_category == "default" or not intent_category:
                        alt_intent = quality_changes_container.getMetaDataEntry("intent", "")
                        if alt_intent and alt_intent != "default":
                            intent_category = alt_intent
                        else:
                            intent_category = "default"
                                        
                    # Create a profile entry for quality changes (user-defined)
                    profile_entry = {
                        'display_name': f"* {quality_name}",  # Star indicates user-defined
                        'container': quality_changes_container,
                        'intent': intent_category,
                        'quality_name': quality_name,
                        'quality_group': None,
                        'quality_type': quality_type,
                        'is_available': True,
                        'is_user_defined': True
                    }
                    
                    self._quality_profiles.append(profile_entry)
                    
                except Exception as profile_error:
                    Logger.log("w", f"Error processing quality changes container {quality_changes_container.getId()}: {profile_error}")
                    continue
            
            # Sort profiles by intent category, then quality name
            self._quality_profiles.sort(key=lambda x: (x['intent'], x['quality_name']))
            
            # Ensure we have default profiles
            has_default_intent = any(profile['intent'] == 'default' for profile in self._quality_profiles)
            if not has_default_intent and self._quality_profiles:
                Logger.log("w", "No default intent profiles found, creating default entries")
                # Group by quality type to create default profiles
                quality_types = {}
                for profile in self._quality_profiles:
                    quality_type = profile['quality_type']
                    if quality_type not in quality_types:
                        quality_types[quality_type] = profile
                
                # Create default intent versions of each quality type
                for quality_type, representative_profile in quality_types.items():
                    default_profile = {
                        'display_name': representative_profile['quality_name'],
                        'container': representative_profile['container'],
                        'intent': 'default',
                        'quality_name': representative_profile['quality_name'],
                        'quality_group': representative_profile['quality_group'],
                        'quality_type': quality_type,
                        'is_available': True
                    }
                    self._quality_profiles.append(default_profile)
            
            # Summary
            base_profiles_count = len([p for p in self._quality_profiles if not p.get('is_user_defined', False)])
            custom_profiles_count = len([p for p in self._quality_profiles if p.get('is_user_defined', False)])
            self._logMessage(f"Loaded {len(self._quality_profiles)} quality profiles for current configuration.")
            self._logMessage(f"  - {base_profiles_count} machine profiles")
            self._logMessage(f"  - {custom_profiles_count} custom profiles")
            
            # Emit signal with loaded profiles
            self.qualityProfilesLoaded.emit(self._quality_profiles.copy())
                    
        except Exception as main_error:
            Logger.log("e", f"Error loading quality profiles: {main_error}")
            import traceback
            traceback.print_exc()
            self._logMessage("Failed to load quality profiles.", is_error=True)
    
    def calculateTransitionAdjustments(self, transitions):
        """
        UNIFIED ITERATIVE APPROACH: Calculate exact transition points and layer height adjustments
        that the splicing logic will use. Each completed section becomes the immutable base pattern
        for the next transition calculation.
        
        This replaces the old dual-system approach with a single unified algorithm that:
        1. Treats Section 1 as immutable base pattern (starts at Z=0, uses original layer heights)
        2. For each subsequent section, finds perfect layer alignment with the previous section
        3. Calculates exact Z-coordinates where transitions occur (may differ from user boundary)
        4. Adjusts initial layer height of upper section for perfect gap-free transition
        5. Each completed section becomes the base pattern for the next iteration
        
        Args:
            transitions: List of dicts with 'section_number', 'start_height', 'end_height', 
                        'profile_id', 'intent_category', 'intent_container_id'
            
        Returns:
            List of dicts with exact transition info for splicing logic to use:
            - section_num, start_z, end_z: Section boundaries  
            - layer_height, initial_layer_height: Original profile values
            - adjusted_initial: Calculated initial layer height for perfect alignment
            - actual_transition_z: Exact Z where transition occurs (replaces user boundary)
            - alignment_info: Details about the alignment calculation
        """
        try:
            if not transitions:
                return []
            
            application = CuraApplication.getInstance()
            machine_manager = application.getMachineManager()
            global_stack = application.getGlobalContainerStack()
            
            if not global_stack:
                Logger.log("e", "No global stack available")
                return []
            
            # Store original state to restore later
            active_machine = machine_manager.activeMachine
            original_quality_id = active_machine.quality.getId() if active_machine else None
            original_quality_changes_id = active_machine.qualityChanges.getId() if active_machine else None
            original_intent_category = machine_manager.activeIntentCategory
            
            # Check for settings that can affect layer alignment
            support_enable = global_stack.getProperty("support_enable", "value")
            support_structure = global_stack.getProperty("support_structure", "value") if support_enable else None
            adaptive_layer_height_enabled = global_stack.getProperty("adaptive_layer_height_enabled", "value")
            
            # Display warnings if problematic settings are detected
            if adaptive_layer_height_enabled:
                self._logMessage("")
                self._logMessage("⚠️  WARNING: Adaptive Layer Height is enabled!", is_error=True)
                self._logMessage("   Adaptive layer height modifies layer heights dynamically.", is_error=True)
                self._logMessage("   This may not work as expected with transition layer adjustments.", is_error=True)
                self._logMessage("")
            
            if support_enable and support_structure in ["tree", "support_tree_bp"]:
                self._logMessage("")
                self._logMessage("⚠️  WARNING: Tree Support is enabled!", is_error=True)
                self._logMessage("   Tree support generation varies between slices (non-deterministic).", is_error=True)
                self._logMessage("   This can cause floating support structures or other issues at transitions.", is_error=True)
                self._logMessage("")
            
            sections = []
            
            # STEP 1: Collect original profile parameters for each section
            self._logMessage("STEP 1: Collecting profile parameters...")
            for transition in transitions:
                section_num = transition['section_number']
                start_z = transition['start_height']
                end_z = transition['end_height']
                profile_id = transition['profile_id']
                intent_category = transition.get('intent_category')
                intent_container_id = transition.get('intent_container_id')
                
                # Switch to this section's profile to read parameters
                if not self._switchQualityProfile(profile_id, intent_category, intent_container_id):
                    Logger.log("e", f"Failed to switch to profile {profile_id} for section {section_num}")
                    continue
                
                # Read the layer height values from the active profile
                layer_height = global_stack.getProperty("layer_height", "value")
                initial_layer_height = global_stack.getProperty("layer_height_0", "value")
                
                sections.append({
                    'section_num': section_num,
                    'start_z': start_z,  # User-requested boundary
                    'end_z': end_z,     # User-requested boundary  
                    'layer_height': float(layer_height) if layer_height else 0.2,
                    'initial_layer_height': float(initial_layer_height) if initial_layer_height else 0.2,
                    'adjusted_initial': None,  # Will be calculated
                    'actual_transition_z': None,  # Exact Z where transition occurs
                    'profile_id': profile_id,
                    'alignment_info': {}
                })
            
            # STEP 2: ITERATIVE PATTERN MATCHING - Each section becomes base for next
            self._logMessage("STEP 2: Calculating iterative pattern-based transitions...")
            
            for i, current_section in enumerate(sections):
                section_num = current_section['section_num']
                
                if i == 0:
                    # Section 1: Base pattern (immutable)
                    current_section['adjusted_initial'] = current_section['initial_layer_height']
                    
                    # Calculate where Section 1 actually ends (this becomes the pattern)
                    if current_section['end_z'] is not None:
                        # Layer stack: initial_layer_height + N * layer_height
                        remaining_height = current_section['end_z'] - current_section['initial_layer_height']
                        num_regular_layers = max(0, int(remaining_height / current_section['layer_height']))
                        pattern_end_z = current_section['initial_layer_height'] + (num_regular_layers * current_section['layer_height'])
                        
                        # The actual transition Z is where the pattern ACTUALLY ends, not the user boundary
                        current_section['actual_transition_z'] = pattern_end_z
                        
                        current_section['alignment_info'] = {
                            'pattern_end_z': pattern_end_z,
                            'num_regular_layers': num_regular_layers,
                            'is_base_pattern': True
                        }
                        
                        self._logMessage(f"Section {section_num}: BASE PATTERN (immutable)")
                        self._logMessage(f"  Z=0mm to {pattern_end_z:.3f}mm (user boundary: {current_section['end_z']:.1f}mm)")
                        self._logMessage(f"  initial={current_section['initial_layer_height']:.3f}mm + {num_regular_layers} × {current_section['layer_height']:.3f}mm layers")
                    else:
                        # Last section has no end boundary - no actual transition Z to set
                        current_section['actual_transition_z'] = None
                        current_section['alignment_info'] = {'is_base_pattern': True, 'is_last_section': True}
                        self._logMessage(f"Section {section_num}: BASE PATTERN to model end")
                
                else:
                    # Section 2+: Match pattern from previous section
                    prev_section = sections[i-1]
                    user_boundary = current_section['start_z']  # User-requested transition height
                    
                    # FIND CLOSEST LAYER TO USER BOUNDARY:
                    # The user boundary is just a guide. We need to find the actual layer
                    # in the previous section that's closest to this boundary (within ±1 layer height tolerance)
                    
                    original_initial = current_section['initial_layer_height']
                    current_layer_height = current_section['layer_height']
                    
                    # Get the actual end Z from the previous section (ITERATIVE ALGORITHM)
                    if prev_section.get('actual_transition_z') is not None:
                        # Previous section already processed - use its actual transition Z
                        closest_layer_z = prev_section['actual_transition_z']
                        self._logMessage(f"Section {section_num}: Using previous section's actual transition Z={closest_layer_z:.6f}mm")
                    elif 'pattern_end_z' in prev_section['alignment_info']:
                        # First section - use its calculated pattern end
                        closest_layer_z = prev_section['alignment_info']['pattern_end_z']
                        self._logMessage(f"Section {section_num}: Using first section's pattern end Z={closest_layer_z:.6f}mm")
                    else:
                        # Need to find the closest layer in previous section to user boundary
                        prev_initial = prev_section['initial_layer_height']
                        prev_layer_height = prev_section['layer_height']
                        prev_start_z = prev_section['start_z']
                        
                        # Generate all possible layer boundaries in previous section
                        layer_boundaries = []
                        current_z = prev_start_z + prev_initial  # First layer end
                        layer_num = 1
                        
                        # Generate layers until we're well past the user boundary
                        while current_z <= user_boundary + prev_layer_height:
                            layer_boundaries.append((layer_num, current_z))
                            current_z += prev_layer_height
                            layer_num += 1
                        
                        # Find the layer boundary closest to user boundary within tolerance
                        tolerance = prev_layer_height  # ±1 layer height tolerance
                        valid_boundaries = [
                            (layer_num, z) for layer_num, z in layer_boundaries 
                            if abs(z - user_boundary) <= tolerance
                        ]
                        
                        if valid_boundaries:
                            # Choose the closest boundary
                            closest_boundary = min(valid_boundaries, key=lambda x: abs(x[1] - user_boundary))
                            closest_layer_z = closest_boundary[1]
                            closest_layer_num = closest_boundary[0]
                            
                            self._logMessage(f"Section {section_num}: Found closest layer {closest_layer_num} at Z={closest_layer_z:.6f}mm")
                            self._logMessage(f"  User boundary: Z={user_boundary:.3f}mm, difference: {closest_layer_z - user_boundary:+.6f}mm")
                        else:
                            # Fallback: use the layer end closest to user boundary
                            closest_boundary = min(layer_boundaries, key=lambda x: abs(x[1] - user_boundary))
                            closest_layer_z = closest_boundary[1]
                            closest_layer_num = closest_boundary[0]
                            
                            self._logMessage(f"Section {section_num}: No layers within tolerance, using closest layer {closest_layer_num} at Z={closest_layer_z:.6f}mm", is_error=True)
                    
                    # This becomes our actual transition point
                    actual_prev_end_z = closest_layer_z
                    
                    # MODULO CALCULATION FOR TRIMMED SECTIONS:
                    # The layer_height_0 (initial layer height) only affects the build plate layer.
                    # Since Section 2+ are trimmed, we need to calculate what layer_height_0 value
                    # will produce the correct layer pattern at the user_boundary (trim point).
                    #
                    # We want the first layer after trimming to align with where the previous section ended.
                    # Formula: layer_height_0 = (ending_z_of_previous_section) % (current_layer_height)
                    
                    calculated_initial = actual_prev_end_z % current_layer_height
                    
                    # Handle floating point precision issues by rounding to 6 decimal places
                    calculated_initial = round(calculated_initial, 6)
                    
                    # Handle edge case where modulo gives very small value (essentially 0)
                    if calculated_initial < 0.001:
                        calculated_initial = current_layer_height
                    
                    # Validate the calculated initial layer height is reasonable
                    if calculated_initial > 0 and calculated_initial <= current_layer_height:
                        current_section['adjusted_initial'] = calculated_initial
                        alignment_type = 'modulo_match'
                        gap = 0.0  # Perfect match by design
                        deviation = abs(calculated_initial - original_initial)
                        
                        self._logMessage(f"Section {section_num}: MODULO MATCH -> Previous section ended at Z={actual_prev_end_z:.6f}mm")
                        self._logMessage(f"  Calculated initial: {actual_prev_end_z:.6f} % {current_layer_height:.3f} = {calculated_initial:.6f}mm")
                    else:
                        # Fallback to original if calculation produces invalid result
                        current_section['adjusted_initial'] = original_initial
                        alignment_type = 'fallback_invalid_modulo'
                        gap = abs(actual_prev_end_z - user_boundary)
                        deviation = 0.0
                        
                        self._logMessage(f"Section {section_num}: Invalid modulo result ({calculated_initial:.6f}mm), using original", is_error=True)
                        
                    # Calculate where THIS section will end (becomes pattern for next section)
                    if current_section['end_z'] is not None:
                        # ITERATIVE BOUNDARY ADJUSTMENT: Calculate layer pattern and find actual transition
                        # within ±1 layer tolerance of user boundary
                        
                        user_end_boundary = current_section['end_z']
                        
                        # Generate all possible layer ends for this section
                        # NOTE: adjusted_initial is only a profile parameter - actual layers use layer_height
                        layer_boundaries = []
                        current_z = actual_prev_end_z + current_section['layer_height']  # First layer end
                        layer_num = 1
                        
                        # Generate layers until we're well past the user boundary
                        while current_z <= user_end_boundary + current_section['layer_height']:
                            # Round to avoid floating point precision issues
                            layer_boundaries.append((layer_num, round(current_z, 6)))
                            current_z += current_section['layer_height']
                            layer_num += 1
                        
                        # Find the natural end of the pattern within user boundary region
                        # The user boundary is a guideline - validate if natural pattern fits within tolerance
                        tolerance = current_section['layer_height']
                        
                        # Find the last layer that is <= user_end_boundary + tolerance
                        valid_boundaries = [
                            (layer_num, z) for layer_num, z in layer_boundaries 
                            if z <= user_end_boundary + tolerance
                        ]
                        
                        if valid_boundaries:
                            # Use the natural end of the pattern (last valid layer)
                            closest_end_boundary = valid_boundaries[-1]  # Last layer within boundary + tolerance
                            this_pattern_end_z = closest_end_boundary[1]
                            closest_end_layer_num = closest_end_boundary[0]
                            
                            # Validate it's within tolerance of user boundary
                            difference = this_pattern_end_z - user_end_boundary
                            if abs(difference) <= tolerance:
                                self._logMessage(f"  Section {section_num} ends at layer {closest_end_layer_num}, Z={this_pattern_end_z:.6f}mm")
                                self._logMessage(f"  User end boundary: Z={user_end_boundary:.1f}mm, difference: {difference:+.6f}mm (within tolerance)")
                            else:
                                self._logMessage(f"  Section {section_num} ends at layer {closest_end_layer_num}, Z={this_pattern_end_z:.6f}mm")
                                self._logMessage(f"  User end boundary: Z={user_end_boundary:.1f}mm, difference: {difference:+.6f}mm (WARNING: outside tolerance)", is_error=True)
                        else:
                            # Fallback: pattern doesn't reach user boundary region
                            if layer_boundaries:
                                closest_end_boundary = layer_boundaries[-1]
                                this_pattern_end_z = closest_end_boundary[1]
                                closest_end_layer_num = closest_end_boundary[0]
                                
                                self._logMessage(f"  Section {section_num}: Pattern ends before user boundary at layer {closest_end_layer_num}, Z={this_pattern_end_z:.6f}mm", is_error=True)
                                self._logMessage(f"  User end boundary: Z={user_end_boundary:.1f}mm, pattern falls short by {user_end_boundary - this_pattern_end_z:.6f}mm", is_error=True)
                            else:
                                self._logMessage(f"  Section {section_num}: No valid layer boundaries generated", is_error=True)
                                this_pattern_end_z = user_end_boundary
                                closest_end_layer_num = 0
                        
                        # Calculate the number of regular layers in this section
                        section_height = this_pattern_end_z - actual_prev_end_z
                        num_regular_layers = max(0, int((section_height - current_section['adjusted_initial']) / current_section['layer_height']))
                        
                        # Set actual_transition_z to where THIS section actually ends (for next section to use)
                        current_section['actual_transition_z'] = this_pattern_end_z
                        
                        current_section['alignment_info'] = {
                            'pattern_end_z': this_pattern_end_z,
                            'num_regular_layers': num_regular_layers,
                            'base_pattern_end_z': actual_prev_end_z,
                            'alignment_type': alignment_type,
                            'gap_with_base': gap,
                            'initial_deviation': deviation
                        }
                    else:
                        # Last section - no end boundary, so no specific actual_transition_z
                        current_section['actual_transition_z'] = None
                        current_section['alignment_info'] = {
                            'base_pattern_end_z': actual_prev_end_z,
                            'alignment_type': alignment_type,
                            'gap_with_base': gap,
                            'initial_deviation': deviation,
                            'is_last_section': True
                        }
                    
                    # Logging
                    if current_section['end_z'] is not None:
                        self._logMessage(f"Section {section_num}: PATTERN MATCH -> Section {i}")
                        self._logMessage(f"  Actual transition: Z={actual_prev_end_z:.6f}mm to {this_pattern_end_z:.6f}mm")
                        self._logMessage(f"  User requested: Z={user_boundary:.1f}mm to {current_section['end_z']:.1f}mm")
                    else:
                        self._logMessage(f"Section {section_num}: PATTERN MATCH -> Section {i} (to end)")
                        self._logMessage(f"  Actual transition: Z={actual_prev_end_z:.6f}mm to model end")
                        self._logMessage(f"  User requested: Z={user_boundary:.1f}mm to model end")
                    
                    if alignment_type != 'no_adjustment_needed':
                        self._logMessage(f"  initial={original_initial:.3f}mm -> {current_section['adjusted_initial']:.6f}mm ({alignment_type}, Δ={current_section['adjusted_initial']-original_initial:+.6f}mm)")
                        self._logMessage(f"  previous section ended at {actual_prev_end_z:.6f}mm, gap={gap:.3f}mm")
            
            # Restore original profile
            if original_quality_changes_id and original_quality_changes_id.lower() not in ["empty", "not_supported", "none"]:
                self._switchQualityProfile(original_quality_changes_id, original_intent_category)
            elif original_quality_id and original_quality_id.lower() not in ["empty", "not_supported", "none"]:
                self._switchQualityProfile(original_quality_id, original_intent_category)
            
            return sections
            
        except Exception as e:
            Logger.log("e", f"Error calculating transition adjustments: {e}")
            import traceback
            traceback.print_exc()
            self._logMessage(f"Failed to calculate adjustments: {e}", is_error=True)
            return []
    
    def _switchQualityProfile(self, profile_id: str, intent_category: str = None, intent_container_id: str = None) -> bool:
        """Switch to the specified quality profile using the centralized service."""
        try:
            return self._profile_service.switch_to_profile(profile_id, intent_category, intent_container_id)
        except ProfileSwitchError as e:
            Logger.log("e", f"Profile switch failed: {e}")
            return False
        except Exception as e:
            Logger.logException("e", f"Unexpected error switching quality profile: {str(e)}")
            return False
    
    def applyLayerHeightAdjustment(self, profile_container, adjusted_initial_height):
        """Apply the calculated initial layer height adjustment to a profile and trigger settings update."""
        try:
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            
            if not global_stack:
                Logger.log("e", "No global stack available")
                return False
            
            # Get the user changes container
            user_changes = global_stack.userChanges
            
            # Set the adjusted initial layer height
            user_changes.setProperty("layer_height_0", "value", adjusted_initial_height)
            
            # Trigger settings update to invalidate engine state
            # This will cause Cura to naturally re-slice when needed
            global_stack.propertyChanged.emit("layer_height_0", "value")
            application.getBackend().needsReprocessing()
            
            return True
            
        except Exception as e:
            Logger.log("e", f"Error applying layer height adjustment: {e}")
            return False
    
    def clearLayerHeightAdjustment(self):
        """Clear any initial layer height adjustments from user changes."""
        try:
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            
            if not global_stack:
                return
            
            user_changes = global_stack.userChanges
            
            # Remove the override
            if user_changes.hasProperty("layer_height_0", "value"):
                user_changes.removeInstance("layer_height_0")
                
        except Exception as e:
            Logger.log("w", f"Error clearing layer height adjustment: {e}")
    
    def _calculateAlignmentOptions(self, base_pattern_end_z, user_boundary, original_initial, base_layer_height):
        """Calculate alignment options when original settings don't produce perfect alignment."""
        # Option 1: Align AT the pattern end (same Z level)
        option1_initial = base_pattern_end_z - user_boundary
        option1_gap = 0.0  # Perfect alignment
        
        # Option 2: Align ABOVE the pattern end (one base pattern layer higher)
        option2_initial = (base_pattern_end_z + base_layer_height) - user_boundary  
        option2_gap = base_layer_height  # Intentional gap = one base layer
        
        # Choose the option that results in a positive initial layer height
        # and is closest to the original initial layer height
        valid_options = []
        if option1_initial > 0:
            valid_options.append(('align_at', option1_gap, abs(option1_initial - original_initial)))
        if option2_initial > 0:
            valid_options.append(('align_above', option2_gap, abs(option2_initial - original_initial)))
        
        if not valid_options:
            return 'no_valid_options', 0.0, 0.0
        else:
            # Choose the option with minimal deviation from original
            best_option = min(valid_options, key=lambda x: x[2])
            return best_option[0], best_option[1], best_option[2]
