# HellaFusion Plugin for Cura
# Based on work by GregValiant (Greg Foresi) and HellAholic
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from dataclasses import dataclass
from typing import Optional, Dict


@dataclass
class TransitionData:
    """
    Immutable data class representing a single section's transition information.
    
    This is the SINGLE SOURCE OF TRUTH for where a section starts, ends, and
    what layer heights it uses. All other code must reference these values.
    """
    
    # Section identification
    section_num: int
    profile_id: str
    profile_name: Optional[str] = None
    
    # User-requested boundaries (guidelines)
    user_start_z: float = 0.0
    user_end_z: Optional[float] = None
    
    # ACTUAL calculated boundaries (AUTHORITATIVE)
    actual_start_z: float = 0.0
    actual_end_z: Optional[float] = None
    
    # Layer height parameters from profile
    layer_height: float = 0.2
    original_initial_layer_height: float = 0.2
    adjusted_initial_layer_height: float = 0.2
    material_shrinkage_percentage_z: float = 100.0
    
    # Layer numbering
    start_layer_num: Optional[int] = None
    end_layer_num: Optional[int] = None
    total_layers: Optional[int] = None
    
    # Retraction settings from profile
    retraction_enabled: bool = True
    retraction_amount: float = 2.0
    retraction_speed: float = 35.0
    prime_speed: float = 30.0
    
    # Alignment and validation info
    alignment_type: str = "unknown"  # 'base_pattern', 'modulo_match', etc.
    gap_with_previous: float = 0.0
    deviation_from_user: float = 0.0
    
    # Additional metadata
    metadata: Dict = None
    
    def __post_init__(self):
        """Initialize metadata dict if not provided."""
        if self.metadata is None:
            object.__setattr__(self, 'metadata', {})
    
    @staticmethod
    def convert_from_cura(value: float, shrinkage_factor: float, apply_compensation: bool = True) -> float:
        """Convert layer height from Cura format (with shrinkage applied) to actual value.
        
        Cura multiplies layer heights by (shrinkage_factor / 100) before we can read them.
        To get the actual value for calculations, we need to reverse this:
        actual_value = cura_value / (shrinkage_factor / 100) = cura_value * 100 / shrinkage_factor
        
        Args:
            value: Layer height value as read from Cura
            shrinkage_factor: material_shrinkage_percentage_z (e.g., 100.1)
            apply_compensation: If False, skip shrinkage compensation (return value as-is)
        
        Returns:
            Actual layer height value for plugin calculations
        """
        if not apply_compensation or shrinkage_factor == 0:
            return value  # Skip compensation or avoid division by zero
        return (value * 100.0) / shrinkage_factor
    
    @staticmethod
    def convert_to_cura(value: float, shrinkage_factor: float, apply_compensation: bool = True) -> float:
        """Convert layer height from actual value to Cura format (with shrinkage applied).
        
        When setting layer heights back to Cura, we need to apply shrinkage compensation:
        cura_value = actual_value * (shrinkage_factor / 100)
        
        Args:
            value: Actual layer height value from plugin calculations
            shrinkage_factor: material_shrinkage_percentage_z (e.g., 100.1)
            apply_compensation: If False, skip shrinkage compensation (return value as-is)
        
        Returns:
            Layer height value in Cura format (with shrinkage applied)
        """
        if not apply_compensation:
            return value  # Skip compensation
        return value * (shrinkage_factor / 100.0)
    
    @property
    def is_first_section(self) -> bool:
        """Check if this is the first section (starts at Z=0)."""
        return self.section_num == 1
    
    @property
    def is_last_section(self) -> bool:
        """Check if this is the last section (no end boundary)."""
        return self.user_end_z is None
    
    @property
    def needs_initial_adjustment(self) -> bool:
        """Check if initial layer height was adjusted from original."""
        return abs(self.adjusted_initial_layer_height - self.original_initial_layer_height) > 0.0001
    
    @property
    def section_height(self) -> Optional[float]:
        """Calculate total height of this section."""
        if self.actual_end_z is None:
            return None
        return self.actual_end_z - self.actual_start_z
    
    def get_summary(self) -> str:
        """Get human-readable summary of this transition."""
        lines = []
        lines.append(f"Section {self.section_num}: {self.profile_name or self.profile_id}")
        
        # Boundaries
        if self.is_last_section:
            lines.append(f"  Z Range: {self.actual_start_z:.3f}mm → Top")
            lines.append(f"  User Requested: {self.user_start_z:.1f}mm → Top")
        else:
            lines.append(f"  Z Range: {self.actual_start_z:.3f}mm → {self.actual_end_z:.3f}mm")
            lines.append(f"  User Requested: {self.user_start_z:.1f}mm → {self.user_end_z:.1f}mm")
        
        # Layer info
        if self.needs_initial_adjustment:
            lines.append(f"  Layer Heights: initial={self.original_initial_layer_height:.3f}mm → {self.adjusted_initial_layer_height:.3f}mm (adjusted), regular={self.layer_height:.3f}mm")
        else:
            lines.append(f"  Layer Heights: initial={self.original_initial_layer_height:.3f}mm, regular={self.layer_height:.3f}mm")
        
        # Alignment
        lines.append(f"  Alignment: {self.alignment_type}")
        if self.gap_with_previous > 0.0001:
            lines.append(f"  Gap: {self.gap_with_previous:.3f}mm")
        if self.deviation_from_user > 0.1:
            lines.append(f"  ⚠️  Deviation from user boundary: {self.deviation_from_user:.3f}mm")
        
        return "\n".join(lines)
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate this transition data for consistency and physical validity.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check basic parameters
        if self.layer_height <= 0:
            errors.append(f"Section {self.section_num}: Invalid layer_height {self.layer_height}")
        
        if self.adjusted_initial_layer_height <= 0:
            errors.append(f"Section {self.section_num}: Invalid adjusted_initial_layer_height {self.adjusted_initial_layer_height}")
        
        if self.adjusted_initial_layer_height > self.layer_height * 4:
            errors.append(f"Section {self.section_num}: adjusted_initial_layer_height ({self.adjusted_initial_layer_height:.3f}) is unusually large compared to layer_height ({self.layer_height:.3f})")
        
        # Check Z boundaries
        if not self.is_first_section and self.actual_start_z <= 0:
            errors.append(f"Section {self.section_num}: actual_start_z must be > 0 for non-first sections")
        
        if self.actual_end_z is not None:
            if self.actual_end_z <= self.actual_start_z:
                errors.append(f"Section {self.section_num}: actual_end_z ({self.actual_end_z:.3f}) must be > actual_start_z ({self.actual_start_z:.3f})")
        
        # Check deviation from user expectations
        if abs(self.actual_start_z - self.user_start_z) > self.layer_height * 2:
            errors.append(f"Section {self.section_num}: Large deviation from user start boundary ({abs(self.actual_start_z - self.user_start_z):.3f}mm)")
        
        if self.user_end_z is not None and self.actual_end_z is not None:
            if abs(self.actual_end_z - self.user_end_z) > self.layer_height * 2:
                errors.append(f"Section {self.section_num}: Large deviation from user end boundary ({abs(self.actual_end_z - self.user_end_z):.3f}mm)")
        
        # Check gap
        if self.gap_with_previous > 0.01:  # More than 10 microns
            errors.append(f"Section {self.section_num}: Non-zero gap with previous section ({self.gap_with_previous:.3f}mm)")
        
        return (len(errors) == 0, errors)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization or legacy code compatibility."""
        return {
            'section_num': self.section_num,
            'profile_id': self.profile_id,
            'profile_name': self.profile_name,
            'start_z': self.actual_start_z,
            'end_z': self.actual_end_z,
            'layer_height': self.layer_height,
            'initial_layer_height': self.original_initial_layer_height,
            'adjusted_initial': self.adjusted_initial_layer_height,
            'original_initial': self.original_initial_layer_height,
            'actual_transition_z': self.actual_end_z,
            'material_shrinkage_percentage_z': self.material_shrinkage_percentage_z,
            'alignment_info': {
                'alignment_type': self.alignment_type,
                'gap_with_base': self.gap_with_previous,
                'deviation': self.deviation_from_user
            },
            'profile_retraction_settings': {
                'retraction_enabled': self.retraction_enabled,
                'retraction_amount': self.retraction_amount,
                'retraction_speed': self.retraction_speed,
                'prime_speed': self.prime_speed
            }
        }
