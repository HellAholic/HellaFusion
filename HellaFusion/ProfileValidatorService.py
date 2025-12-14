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
                 message: str, check_function: callable):
        """
        Initialize a validation rule.
        
        Args:
            rule_id: Unique identifier for this rule
            setting_key: The Cura setting key to check (e.g., 'support_enable')
            severity: ValidationSeverity.WARNING or ValidationSeverity.ERROR
            message: User-friendly message to display when rule is triggered
            check_function: Function that takes (setting_value) and returns True if issue exists
        """
        self.rule_id = rule_id
        self.setting_key = setting_key
        self.severity = severity
        self.message = message
        self.check_function = check_function
    
    def validate(self, setting_value: Any) -> Optional[ValidationIssue]:
        """
        Validate a setting value against this rule.
        
        Args:
            setting_value: The value of the setting to check
            
        Returns:
            ValidationIssue if the rule is triggered, None otherwise
        """
        try:
            result = self.check_function(setting_value)
            
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
            check_function=lambda value: value is True or (isinstance(value, str) and value.lower() == "true")
        ))
        
        # Rule 2: Tree support structure (Error)
        rules.append(ValidationRule(
            rule_id="tree_support",
            setting_key="support_structure",
            severity=ValidationSeverity.ERROR,
            message="Tree support structure is enabled. This is not compatible with HellaFusion and must be changed or overridden.",
            check_function=lambda value: value == "tree"
        ))
        
        # Rule 3: Raft adhesion (Warning)
        rules.append(ValidationRule(
            rule_id="raft_adhesion",
            setting_key="adhesion_type",
            severity=ValidationSeverity.WARNING,
            message="Raft bed adhesion is enabled. This may affect transition height calculations.",
            check_function=lambda value: value == "raft"
        ))
        
        # Rule 4: One at a time print sequence (Error)
        rules.append(ValidationRule(
            rule_id="one_at_a_time",
            setting_key="print_sequence",
            severity=ValidationSeverity.ERROR,
            message="'One at a Time' print sequence is enabled. This is not compatible with HellaFusion and must be changed or overridden.",
            check_function=lambda value: value == "one_at_a_time"
        ))
        
        # Rule 5: Adaptive layers (Warning)
        # Note: Cura may return boolean True or string "true" depending on the source
        rules.append(ValidationRule(
            rule_id="adaptive_layers",
            setting_key="adaptive_layer_height_enabled",
            severity=ValidationSeverity.WARNING,
            message="Adaptive layers are enabled. This may interfere with HellaFusion's layer height calculations.",
            check_function=lambda value: value is True or (isinstance(value, str) and value.lower() == "true")
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
                issue = rule.validate(setting_value)
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
