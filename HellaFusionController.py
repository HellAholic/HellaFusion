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
from .TransitionCalculator import TransitionCalculator


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

        # Connect to machine change signals for automatic profile reloading
        self._connectMachineChangeSignals()

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
    
    def _connectMachineChangeSignals(self):
        """Connect to machine change signals to automatically update quality profiles."""
        try:
            application = CuraApplication.getInstance()
            
            # Connect to global container stack changes (when machine is switched)
            if hasattr(application, 'globalContainerStackChanged'):
                application.globalContainerStackChanged.connect(self._onMachineChanged)
            
            # Connect to machine manager signals
            machine_manager = application.getMachineManager()
            if hasattr(machine_manager, 'globalContainerChanged'):
                machine_manager.globalContainerChanged.connect(self._onMachineChanged)
            
            # Connect to container tree changes (when profiles are added/modified)
            from cura.Machines.ContainerTree import ContainerTree
            container_tree = ContainerTree.getInstance()
            if hasattr(container_tree, 'containerTreeChanged'):
                container_tree.containerTreeChanged.connect(self._onMachineChanged)
            
            # Connect to container registry signals (for profile save/update detection)
            container_registry = application.getContainerRegistry()
            if hasattr(container_registry, 'containerAdded'):
                container_registry.containerAdded.connect(self._onContainerAdded)
            
            if hasattr(container_registry, 'containerMetaDataChanged'):
                container_registry.containerMetaDataChanged.connect(self._onContainerMetaDataChanged)
            
        except Exception as e:
            Logger.log("w", f"Could not connect to some machine change signals: {e}")

    def _onMachineChanged(self):
        """Handle machine change events by refreshing quality profiles."""
        try:
            Logger.log("i", "Machine or profile configuration changed - automatically reloading quality profiles")
            # Use a short delay to allow Cura to finish updating its internal state
            QTimer.singleShot(500, self._loadQualityProfiles)

        except Exception as e:
            Logger.log("e", f"Error handling machine change: {e}")

    def _onContainerAdded(self, container):
        """Handle new container added - reload if it's a quality_changes profile."""
        try:
            # Check if it's a quality_changes container (custom profile)
            if container and hasattr(container, 'getMetaDataEntry'):
                container_type = container.getMetaDataEntry("type", "")
                if container_type == "quality_changes":
                    container_name = container.getName() if hasattr(container, 'getName') else "Unknown"
                    Logger.log("i", f"New quality profile '{container_name}' saved - automatically reloading")
                    # Use a short delay to allow Cura to finish updating
                    QTimer.singleShot(500, self._loadQualityProfiles)

        except Exception as e:
            Logger.log("w", f"Error handling container added: {e}")

    def _onContainerMetaDataChanged(self, container):
        """Handle container metadata changed - reload if it's a quality_changes profile."""
        try:
            # Check if it's a quality_changes container (custom profile update)
            if container and hasattr(container, 'getMetaDataEntry'):
                container_type = container.getMetaDataEntry("type", "")
                if container_type == "quality_changes":
                    container_name = container.getName() if hasattr(container, 'getName') else "Unknown"
                    Logger.log("i", f"Quality profile '{container_name}' updated - automatically reloading")
                    # Use a short delay to allow Cura to finish updating
                    QTimer.singleShot(500, self._loadQualityProfiles)

        except Exception as e:
            Logger.log("w", f"Error handling container metadata changed: {e}")

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
        Calculate exact transition points using TransitionCalculator.
        
        This method delegates to TransitionCalculator (single source of truth) which implements
        the planofaction.md algorithm exactly. The 400-line inline calculation has been replaced
        with this ~100-line wrapper that focuses on profile switching and format conversion.
        
        Args:
            transitions: List of dicts with 'section_number', 'start_height', 'end_height', 
                        'profile_id', 'intent_category', 'intent_container_id'
            
        Returns:
            List of dicts with exact transition info (backward compatible format for Logic)
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
            
            # Check for problematic settings
            support_enable = global_stack.getProperty("support_enable", "value")
            support_structure = global_stack.getProperty("support_structure", "value") if support_enable else None
            adaptive_layer_height_enabled = global_stack.getProperty("adaptive_layer_height_enabled", "value")
            
            # Display warnings if problematic settings are detected
            if adaptive_layer_height_enabled:
                self._logMessage("")
                self._logMessage("⚠️  WARNING: Adaptive Layer Height is enabled!", is_error=True)
                self._logMessage("   Adaptive layers may not work correctly with transition adjustments.", is_error=True)
                self._logMessage("")
            
            if support_enable and support_structure in ["tree", "support_tree_bp"]:
                self._logMessage("")
                self._logMessage("⚠️  WARNING: Tree Support is enabled!", is_error=True)
                self._logMessage("   Tree support can cause issues at transitions (non-deterministic).", is_error=True)
                self._logMessage("")
            
            # Convert transitions to format expected by TransitionCalculator
            sections_config = []
            for transition in transitions:
                sections_config.append({
                    'section_number': transition['section_number'],
                    'start_height': transition['start_height'],
                    'end_height': transition['end_height'],
                    'profile_id': transition['profile_id'],
                    'intent_category': transition.get('intent_category'),
                    'intent_container_id': transition.get('intent_container_id')
                })
            
            # Create profile reader callback that switches profiles and reads parameters
            def profile_reader(profile_id, intent_category, intent_container_id):
                """Read profile parameters by switching to the profile."""
                if not self._switchQualityProfile(profile_id, intent_category, intent_container_id):
                    Logger.log("e", f"Failed to switch to profile {profile_id}")
                    return None
                
                # Read parameters from active profile
                extruders = global_stack.extruderList
                if not extruders:
                    return None
                
                # Import TransitionData for conversion helpers
                from .TransitionData import TransitionData
                
                # Read raw values from Cura (these have shrinkage compensation already applied)
                layer_height_raw = float(global_stack.getProperty("layer_height", "value") or 0.2)
                initial_layer_height_raw = float(global_stack.getProperty("layer_height_0", "value") or 0.2)
                shrinkage_factor = float(global_stack.getProperty("material_shrinkage_percentage_z", "value") or 100.0)
                
                # Convert from Cura format to actual values for plugin calculations
                layer_height_actual = TransitionData.convert_from_cura(layer_height_raw, shrinkage_factor)
                initial_layer_height_actual = TransitionData.convert_from_cura(initial_layer_height_raw, shrinkage_factor)
                
                return {
                    'layer_height': layer_height_actual,
                    'initial_layer_height': initial_layer_height_actual,
                    'retraction_enabled': bool(extruders[0].getProperty("retraction_enable", "value")),
                    'retraction_amount': float(extruders[0].getProperty("retraction_amount", "value") or 2.0),
                    'retraction_speed': float(extruders[0].getProperty("retraction_retract_speed", "value") or 35.0),
                    'prime_speed': float(extruders[0].getProperty("retraction_prime_speed", "value") or 30.0),
                    'material_shrinkage_percentage_z': shrinkage_factor,
                    'profile_name': global_stack.quality.getName() if global_stack.quality else "Unknown"
                }

            self._logMessage("═" * 80)
            self._logMessage("USING TRANSITIONCALCULATOR ")
            self._logMessage("═" * 80)
            
            calculator = TransitionCalculator()
            transition_data_list = calculator.calculate_all_transitions(sections_config, profile_reader)
            
            # Log calculation results
            for td in transition_data_list:
                self._logMessage("")
                self._logMessage(td.get_summary())
            
            self._logMessage("")
            
            # Check for validation errors
            if calculator.has_errors():
                self._logMessage("═" * 80)
                self._logMessage("⚠️  VALIDATION ERRORS DETECTED:", is_error=True)
                self._logMessage("═" * 80)
                for error in calculator.get_validation_errors():
                    self._logMessage(f"  • {error}", is_error=True)
                self._logMessage("")
            else:
                self._logMessage("✅ All transition validations passed!")
            
            self._logMessage("═" * 80)
            
            # Convert TransitionData objects to backward-compatible dict format for Logic
            # This maintains compatibility with existing HellaFusionLogic.combineGcodeFiles()
            sections = []
            for td in transition_data_list:
                section_dict = {
                    'section_num': td.section_num,
                    'start_z': td.user_start_z,
                    'end_z': td.user_end_z,
                    'layer_height': td.layer_height,
                    'initial_layer_height': td.original_initial_layer_height,
                    'adjusted_initial': td.adjusted_initial_layer_height,
                    'actual_transition_z': td.actual_end_z,
                    'profile_id': td.profile_id,
                    'alignment_info': {
                        'pattern_end_z': td.actual_end_z,
                        'alignment_type': td.alignment_type,
                        'is_base_pattern': td.is_first_section,
                        'is_last_section': td.is_last_section
                    },
                    'material_shrinkage_percentage_z': td.material_shrinkage_percentage_z,
                    '_transition_data': td
                }
                sections.append(section_dict)
            
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
    
    def applyLayerHeightAdjustment(self, profile_container, adjusted_initial_height, shrinkage_factor):
        """Apply the calculated initial layer height adjustment to a profile and trigger settings update.
        
        Args:
            profile_container: The profile container to modify
            adjusted_initial_height: The ACTUAL calculated initial layer height (not Cura format)
            shrinkage_factor: material_shrinkage_percentage_z value
        """
        try:
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            
            if not global_stack:
                Logger.log("e", "No global stack available")
                return False
            
            # Import TransitionData for conversion helpers
            from .TransitionData import TransitionData
            
            # Get the user changes container
            user_changes = global_stack.userChanges

            # Convert from actual value to Cura format (apply shrinkage compensation)
            # The adjusted_initial_height is in actual units, we need to convert to Cura format
            adjusted_initial_height_cura = TransitionData.convert_to_cura(
                float(adjusted_initial_height), 
                shrinkage_factor
            )
            
            # Set the adjusted initial layer height in Cura format
            user_changes.setProperty("layer_height_0", "value", adjusted_initial_height_cura)
            
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
