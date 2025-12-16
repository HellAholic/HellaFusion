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

from enum import Enum
from typing import List, Dict, Any, Optional
from UM.Logger import Logger
from cura.CuraApplication import CuraApplication
from cura.Machines.ContainerTree import ContainerTree


class ValidationSeverity(Enum):
    """Severity levels for profile validation issues."""
    WARNING = "warning"
    ERROR = "error"


class ValidationIssue:
    """Represents a validation issue found in a profile."""
    
    def __init__(self, setting_key: str, severity: ValidationSeverity, message: str, 
                 found_value: Any = None, rule_id: str = None):
        self.setting_key = setting_key
        self.severity = severity
        self.message = message
        self.found_value = found_value
        self.rule_id = rule_id or setting_key
    
    def __repr__(self):
        return f"ValidationIssue({self.severity.value}: {self.message})"
    
    def is_error(self) -> bool:
        """Check if this is an error-level issue."""
        return self.severity == ValidationSeverity.ERROR
    
    def is_warning(self) -> bool:
        """Check if this is a warning-level issue."""
        return self.severity == ValidationSeverity.WARNING


class ValidationRule:
    """Defines a validation rule for checking profile settings."""
    
    def __init__(self, rule_id: str, setting_key: str, severity: ValidationSeverity,
                 message: str, check_function: callable, requires_settings: List[str] = None):
        """
        Initialize a validation rule.
        
        Args:
            rule_id: Unique identifier for this rule
            setting_key: The Cura setting key to check (e.g., 'support_enable')
            severity: ValidationSeverity.WARNING or ValidationSeverity.ERROR
            message: User-friendly message to display when rule is triggered
            check_function: Function that takes (setting_value, all_settings) and returns True if issue exists
            requires_settings: Optional list of additional setting keys needed for validation
        """
        self.rule_id = rule_id
        self.setting_key = setting_key
        self.severity = severity
        self.message = message
        self.check_function = check_function
        self.requires_settings = requires_settings or []
    
    def validate(self, setting_value: Any, all_settings: Dict[str, Any] = None) -> Optional[ValidationIssue]:
        """
        Validate a setting value against this rule.
        
        Args:
            setting_value: The value of the setting to check
            all_settings: Dictionary of all profile settings (for context-aware validation)
            
        Returns:
            ValidationIssue if the rule is triggered, None otherwise
        """
        try:
            # Pass both the specific value and all settings for context-aware validation
            result = self.check_function(setting_value, all_settings or {})
            
            if result:
                return ValidationIssue(
                    setting_key=self.setting_key,
                    severity=self.severity,
                    message=self.message,
                    found_value=setting_value,
                    rule_id=self.rule_id
                )
        except Exception as e:
            Logger.log("w", f"Error checking validation rule {self.rule_id}: {e}")
        
        return None


class ProfileValidatorService:
    """
    Service for validating Cura profile settings against HellaFusion compatibility rules.
    
    This service uses a configuration-driven approach where validation rules are defined
    declaratively, making it easy to add new rules or modify existing ones.
    """
    
    def __init__(self):
        """Initialize the validator with predefined rules."""
        self._rules = self._initialize_validation_rules()
    
    def get_required_settings(self) -> List[str]:
        """
        Get the list of setting keys that need to be read for validation.
        
        Returns:
            List of Cura setting keys required by all validation rules
        """
        return [rule.setting_key for rule in self._rules]
    
    def _initialize_validation_rules(self) -> List[ValidationRule]:
        """
        Initialize all validation rules.
        
        Returns:
            List of ValidationRule objects
        """
        rules = []
        
        # Rule 1: Support enabled (Warning)
        rules.append(ValidationRule(
            rule_id="support_enabled",
            setting_key="support_enable",
            severity=ValidationSeverity.WARNING,
            message="Support is enabled. This may cause issues with HellaFusion transitions.",
            check_function=lambda value, all_settings: value is True or (isinstance(value, str) and value.lower() == "true")
        ))
        
        # Rule 2: Tree support structure (Error)
        # Only triggers if support is actually enabled
        rules.append(ValidationRule(
            rule_id="tree_support",
            setting_key="support_structure",
            severity=ValidationSeverity.ERROR,
            message="Tree support structure is enabled. This is not compatible with HellaFusion and must be changed or overridden.",
            check_function=lambda value, all_settings: (
                value == "tree" and 
                (all_settings.get('support_enable') is True or 
                 (isinstance(all_settings.get('support_enable'), str) and all_settings.get('support_enable').lower() == "true"))
            ),
            requires_settings=["support_enable"]
        ))
        
        # Rule 3: Raft adhesion (Warning)
        rules.append(ValidationRule(
            rule_id="raft_adhesion",
            setting_key="adhesion_type",
            severity=ValidationSeverity.WARNING,
            message="Raft bed adhesion is enabled. This may affect transition height calculations.",
            check_function=lambda value, all_settings: value == "raft"
        ))
        
        # Rule 4: One at a time print sequence (Error)
        rules.append(ValidationRule(
            rule_id="one_at_a_time",
            setting_key="print_sequence",
            severity=ValidationSeverity.ERROR,
            message="'One at a Time' print sequence is enabled. This is not compatible with HellaFusion and must be changed or overridden.",
            check_function=lambda value, all_settings: value == "one_at_a_time"
        ))
        
        # Rule 5: Adaptive layers (Warning)
        # Note: Cura may return boolean True or string "true" depending on the source
        rules.append(ValidationRule(
            rule_id="adaptive_layers",
            setting_key="adaptive_layer_height_enabled",
            severity=ValidationSeverity.WARNING,
            message="Adaptive layers are enabled. This may interfere with HellaFusion's layer height calculations.",
            check_function=lambda value, all_settings: value is True or (isinstance(value, str) and value.lower() == "true")
        ))
        
        return rules
    
    def validate_profile_settings(self, profile_settings: Dict[str, Any]) -> List[ValidationIssue]:
        """
        Validate a profile's settings against all rules.
        
        Args:
            profile_settings: Dictionary of setting_key -> setting_value pairs
            
        Returns:
            List of ValidationIssue objects (empty if no issues found)
        """
        issues = []
        
        for rule in self._rules:
            # Check if the setting exists in the profile
            if rule.setting_key in profile_settings:
                setting_value = profile_settings[rule.setting_key]
                # Pass all settings for context-aware validation
                issue = rule.validate(setting_value, profile_settings)
                if issue:
                    issues.append(issue)
        
        return issues
    
    def has_errors(self, issues: List[ValidationIssue]) -> bool:
        """
        Check if any issues are error-level.
        
        Args:
            issues: List of ValidationIssue objects
            
        Returns:
            True if any error-level issues exist
        """
        return any(issue.is_error() for issue in issues)
    
    def has_warnings(self, issues: List[ValidationIssue]) -> bool:
        """
        Check if any issues are warning-level.
        
        Args:
            issues: List of ValidationIssue objects
            
        Returns:
            True if any warning-level issues exist
        """
        return any(issue.is_warning() for issue in issues)
    
    def get_errors(self, issues: List[ValidationIssue]) -> List[ValidationIssue]:
        """
        Filter issues to only error-level.
        
        Args:
            issues: List of ValidationIssue objects
            
        Returns:
            List of error-level issues only
        """
        return [issue for issue in issues if issue.is_error()]
    
    def get_warnings(self, issues: List[ValidationIssue]) -> List[ValidationIssue]:
        """
        Filter issues to only warning-level.
        
        Args:
            issues: List of ValidationIssue objects
            
        Returns:
            List of warning-level issues only
        """
        return [issue for issue in issues if issue.is_warning()]
    
    def add_custom_rule(self, rule: ValidationRule):
        """
        Add a custom validation rule at runtime.
        
        This allows for dynamic rule addition without modifying the core validator.
        
        Args:
            rule: ValidationRule object to add
        """
        self._rules.append(rule)
    
    def get_all_rules(self) -> List[ValidationRule]:
        """
        Get all registered validation rules.
        
        Returns:
            List of all ValidationRule objects
        """
        return self._rules.copy()
    
    def read_profile_settings(self, profile_data: dict) -> dict:
        """
        Read setting values from a profile by querying the container hierarchy.
        Does not modify the stack - just reads what values would apply if this profile were used.
        
        Args:
            profile_data: Profile data dict from combo box containing 'container_id' and metadata
            
        Returns:
            Dictionary of setting_key -> setting_value pairs
        """
        
        settings = {}
        
        try:
            container_id = profile_data.get('container_id')
            intent_container_id = profile_data.get('intent_container_id')
            
            if not container_id:
                return settings
            
            # Get the application and current stack
            application = CuraApplication.getInstance()
            global_stack = application.getGlobalContainerStack()
            container_registry = application.getContainerRegistry()
            
            if not global_stack:
                return settings
            
            extruder_stacks = global_stack.extruderList
            if not extruder_stacks:
                return settings
            
            extruder_stack = extruder_stacks[0]
            
            # Find the profile container (could be quality or quality_changes)
            profile_containers = container_registry.findInstanceContainers(id=container_id)
            if not profile_containers:
                return settings
            
            profile_container = profile_containers[0]
            container_type = profile_container.getMetaDataEntry("type", "quality")
            
            # Determine which containers have the quality settings
            # Quality profiles have TWO containers: global and extruder-specific
            global_quality_container = None
            extruder_quality_container = None
            
            if container_type == "quality":
                # For regular quality profiles, use ContainerTree to get the quality group
                extruder_quality_container = profile_container
                
                quality_type = profile_container.getMetaDataEntry("quality_type")
                machine_definition = profile_container.getMetaDataEntry("definition")
                
                if quality_type and machine_definition:
                    # Use ContainerTree to get the quality group
                    container_tree = ContainerTree.getInstance()
                    machine_node = container_tree.machines.get(machine_definition)
                    
                    if machine_node:
                        # Get quality groups for the current extruder configuration
                        variant_names = [extruder.variant.getName() for extruder in global_stack.extruderList]
                        material_bases = [extruder.material.getMetaDataEntry("base_file") for extruder in global_stack.extruderList]
                        extruder_enabled = [extruder.isEnabled for extruder in global_stack.extruderList]
                        
                        quality_groups = machine_node.getQualityGroups(variant_names, material_bases, extruder_enabled)
                        
                        # Get the quality group for this quality type
                        if quality_type in quality_groups:
                            quality_group = quality_groups[quality_type]
                            
                            # Get the global quality node
                            if quality_group.node_for_global and quality_group.node_for_global.container:
                                global_quality_container = quality_group.node_for_global.container
                            
                            # Get the extruder quality node for the first extruder (position 0)
                            if 0 in quality_group.nodes_for_extruders:
                                quality_node = quality_group.nodes_for_extruders[0]
                                if quality_node and quality_node.container:
                                    extruder_quality_container = quality_node.container
            
            elif container_type == "quality_changes":
                # For quality_changes, use ContainerTree to find the correct base quality
                quality_type = profile_container.getMetaDataEntry("quality_type")
                machine_definition = profile_container.getMetaDataEntry("definition")
                
                if quality_type and machine_definition:
                    # Use ContainerTree to get the quality groups for this machine
                    container_tree = ContainerTree.getInstance()
                    machine_node = container_tree.machines.get(machine_definition)
                    
                    if machine_node:
                        # Get quality groups for the current extruder configuration
                        variant_names = [extruder.variant.getName() for extruder in extruder_stack.getNextStack().extruderList]
                        material_bases = [extruder.material.getMetaDataEntry("base_file") for extruder in extruder_stack.getNextStack().extruderList]
                        extruder_enabled = [extruder.isEnabled for extruder in extruder_stack.getNextStack().extruderList]
                        
                        quality_groups = machine_node.getQualityGroups(variant_names, material_bases, extruder_enabled)
                        
                        # Get the quality group for this quality type
                        if quality_type in quality_groups:
                            quality_group = quality_groups[quality_type]
                            
                            # Get the global quality node
                            if quality_group.node_for_global and quality_group.node_for_global.container:
                                global_quality_container = quality_group.node_for_global.container
                            
                            # Get the extruder quality node for the first extruder (position 0)
                            if 0 in quality_group.nodes_for_extruders:
                                quality_node = quality_group.nodes_for_extruders[0]
                                if quality_node and quality_node.container:
                                    extruder_quality_container = quality_node.container
            
            # Find the intent container if specified
            intent_container = None
            if intent_container_id and intent_container_id != "empty_intent":
                intent_containers = container_registry.findInstanceContainers(id=intent_container_id)
                if intent_containers:
                    intent_container = intent_containers[0]
            
            # Get setting keys we need to validate
            setting_keys = self.get_required_settings()
            
            # For each setting, search through the container hierarchy
            # Container priority: Intent -> Quality_changes -> Global_Quality -> Extruder_Quality -> Material -> Variant -> DefinitionChanges -> Definition
            for setting_key in setting_keys:
                try:
                    value = None
                    
                    # Check intent container
                    if intent_container and intent_container.hasProperty(setting_key, "value"):
                        value = intent_container.getProperty(setting_key, "value")
                    
                    # Check quality_changes container (user's modified settings)
                    if value is None and container_type == "quality_changes" and profile_container.hasProperty(setting_key, "value"):
                        value = profile_container.getProperty(setting_key, "value")
                    
                    # Check global quality container (has settings like adaptive_layer_height_enabled)
                    if value is None and global_quality_container and global_quality_container.hasProperty(setting_key, "value"):
                        value = global_quality_container.getProperty(setting_key, "value")
                    
                    # Check extruder quality container (has extruder-specific quality settings)
                    if value is None and extruder_quality_container and extruder_quality_container.hasProperty(setting_key, "value"):
                        value = extruder_quality_container.getProperty(setting_key, "value")
                    
                    # Check material (from current stack)
                    if value is None:
                        material = extruder_stack.material
                        if material and material.hasProperty(setting_key, "value"):
                            value = material.getProperty(setting_key, "value")
                    
                    # Check variant (from current stack)
                    if value is None:
                        variant = extruder_stack.variant
                        if variant and variant.hasProperty(setting_key, "value"):
                            value = variant.getProperty(setting_key, "value")
                    
                    # Check definition changes (from current stack)
                    if value is None:
                        def_changes = extruder_stack.definitionChanges
                        if def_changes and def_changes.hasProperty(setting_key, "value"):
                            value = def_changes.getProperty(setting_key, "value")
                    
                    # Check definition (from current stack)
                    if value is None:
                        definition = extruder_stack.definition
                        if definition and definition.hasProperty(setting_key, "value"):
                            value = definition.getProperty(setting_key, "value")
                    
                    if value is not None:
                        settings[setting_key] = value
                        
                except Exception as e:
                    Logger.log("w", f"Could not read setting {setting_key}: {e}")
            
            return settings
            
        except Exception as e:
            Logger.log("e", f"Error reading profile settings: {e}")
            return settings
