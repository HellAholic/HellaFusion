# HellaFusion Plugin for Cura
# Based on work by GregValiant (Greg Foresi) and HellAholic
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from typing import List
from UM.Logger import Logger

from .TransitionData import TransitionData


class TransitionCalculator:
    """
    SINGLE SOURCE OF TRUTH for all transition calculations in HellaFusion.
    
    This class implements the algorithm from planofaction.md exactly:
    
    For Section A (initial):
        layer_number_a_to_b = int((transition_z - layer_height_0_a) / layer_height_a) + 1
        calculated_transition_z_a = ((layer_number_a_to_b - 1) * layer_height_a) + layer_height_0_a
    
    For Section B, C, D... (following):
        calculated_layer_height_0_for_b = section_A_calculated_transition_z % layer_height_b
        layer_number_start_b = ((section_A_calculated_transition_z - calculated_layer_height_0_for_b) / layer_height_b) + 2
    
    Key principles:
    - Section 1 is the immutable base pattern (starts at Z=0)
    - Each following section is calculated based on where previous section ACTUALLY ends
    - Modulo arithmetic ensures perfect gap-free alignment
    - User boundaries are guidelines; actual transitions may differ slightly
    """
    
    def __init__(self):
        """Initialize the calculator."""
        self._transitions: List[TransitionData] = []
        self._validation_errors: List[str] = []
    
    def calculate_all_transitions(
        self, 
        sections_config: List[dict],
        profile_reader: callable
    ) -> List[TransitionData]:
        """
        Calculate exact transition points for all sections using iterative pattern matching.
        
        This is the MAIN ENTRY POINT for transition calculations.
        
        Args:
            sections_config: List of dicts with:
                - section_number: int
                - start_height: float (user-requested)
                - end_height: Optional[float] (user-requested)
                - profile_id: str
                - intent_category: Optional[str]
                - intent_container_id: Optional[str]
            
            profile_reader: Callable that switches to a profile and returns its parameters:
                def read_profile(profile_id, intent_category, intent_container_id) -> dict:
                    return {
                        'layer_height': float,
                        'initial_layer_height': float,
                        'retraction_enabled': bool,
                        'retraction_amount': float,
                        'retraction_speed': float,
                        'prime_speed': float,
                        'profile_name': str
                    }
        
        Returns:
            List of TransitionData objects with exact calculated boundaries
        """
        self._transitions = []
        self._validation_errors = []
        
        if not sections_config:
            Logger.log("e", "TransitionCalculator: No sections provided")
            return []
        
        Logger.log("i", "=" * 60)
        Logger.log("i", "TransitionCalculator: Starting calculation")
        Logger.log("i", "=" * 60)
        
        # STEP 1: Read profile parameters for each section
        profile_params = []
        for section_config in sections_config:
            try:
                params = profile_reader(
                    section_config['profile_id'],
                    section_config.get('intent_category'),
                    section_config.get('intent_container_id')
                )
                
                if not params:
                    Logger.log("e", f"Failed to read profile {section_config['profile_id']}")
                    continue
                
                profile_params.append({
                    **section_config,
                    **params
                })
                
            except Exception as e:
                Logger.log("e", f"Error reading profile for section {section_config['section_number']}: {e}")
                continue
        
        if not profile_params:
            Logger.log("e", "TransitionCalculator: No valid profiles found")
            return []
        
        # STEP 2: Iteratively calculate transitions (each section becomes base for next)
        for i, params in enumerate(profile_params):
            section_num = params['section_number']
            
            if i == 0:
                # Section 1: Base pattern (immutable)
                transition = self._calculate_first_section(params)
            else:
                # Section 2+: Pattern match with previous section
                prev_transition = self._transitions[i - 1]
                transition = self._calculate_following_section(params, prev_transition)
            
            self._transitions.append(transition)
            Logger.log("i", transition.get_summary())
        
        # STEP 3: Validate all transitions
        self._validate_all_transitions()
        
        Logger.log("i", "=" * 60)
        Logger.log("i", f"TransitionCalculator: Completed {len(self._transitions)} sections")
        if self._validation_errors:
            Logger.log("w", f"Validation found {len(self._validation_errors)} issues:")
            for error in self._validation_errors:
                Logger.log("w", f"  - {error}")
        else:
            Logger.log("i", "✓ All transitions validated successfully")
        Logger.log("i", "=" * 60)
        
        return self._transitions
    
    def _calculate_first_section(self, params: dict) -> TransitionData:
        """
        Calculate Section 1 (base pattern).
        
        Section 1 is immutable and starts at Z=0 with its original layer heights.
        It establishes the base pattern that all other sections must align with.
        
        Algorithm:
            layer_number_a_to_b = int((user_end_z - layer_height_0_a) / layer_height_a) + 1
            actual_end_z = ((layer_number_a_to_b - 1) * layer_height_a) + layer_height_0_a
        """
        section_num = params['section_number']
        user_end_z = params.get('end_height')
        layer_height = params['layer_height']
        initial_layer_height = params['initial_layer_height']
        
        # Section 1 always starts at Z=0 with original layer heights
        actual_start_z = 0.0
        adjusted_initial = initial_layer_height  # No adjustment needed
        
        # Calculate where Section 1 actually ends
        actual_end_z = None
        end_layer_num = None
        total_layers = None
        
        if user_end_z is not None:
            # Formula from planofaction.md:
            # layer_number_a_to_b = int((transition_z - layer_height_0_a) / layer_height_a) + 1
            remaining_height = user_end_z - initial_layer_height
            layer_number_a_to_b = int(remaining_height / layer_height) + 1
            
            # actual_end_z = ((layer_number - 1) * layer_height) + layer_height_0
            actual_end_z = ((layer_number_a_to_b - 1) * layer_height) + initial_layer_height
            
            end_layer_num = layer_number_a_to_b
            total_layers = layer_number_a_to_b + 1  # +1 for layer 0
        
        deviation = abs(actual_end_z - user_end_z) if actual_end_z and user_end_z else 0.0
        
        return TransitionData(
            section_num=section_num,
            profile_id=params['profile_id'],
            profile_name=params.get('profile_name'),
            user_start_z=0.0,
            user_end_z=user_end_z,
            actual_start_z=actual_start_z,
            actual_end_z=actual_end_z,
            layer_height=layer_height,
            original_initial_layer_height=initial_layer_height,
            adjusted_initial_layer_height=adjusted_initial,
            material_shrinkage_percentage_z=params.get('material_shrinkage_percentage_z', 100.0),
            start_layer_num=0,
            end_layer_num=end_layer_num,
            total_layers=total_layers,
            retraction_enabled=params.get('retraction_enabled', True),
            retraction_amount=params.get('retraction_amount', 2.0),
            retraction_speed=params.get('retraction_speed', 35.0),
            prime_speed=params.get('prime_speed', 30.0),
            alignment_type='base_pattern',
            gap_with_previous=0.0,
            deviation_from_user=deviation
        )
    
    def _calculate_following_section(
        self, 
        params: dict, 
        prev_transition: TransitionData
    ) -> TransitionData:
        """
        Calculate Section 2+ using iterative pattern matching.
        
        Each section is calculated based on where the previous section ACTUALLY ends,
        not where the user requested it to end.
        
        Algorithm from planofaction.md:
            calculated_layer_height_0_for_b = section_A_calculated_transition_z % layer_height_b
            layer_number_start_b = ((section_A_calculated_transition_z - calculated_layer_height_0_for_b) / layer_height_b) + 2
        """
        section_num = params['section_number']
        user_start_z = params['start_height']
        user_end_z = params.get('end_height')
        layer_height = params['layer_height']
        original_initial = params['initial_layer_height']
        
        # CRITICAL: This section MUST start where previous section ACTUALLY ended
        # This is the ITERATIVE PATTERN MATCHING principle
        actual_start_z = prev_transition.actual_end_z
        
        if actual_start_z is None:
            Logger.log("e", f"Section {section_num}: Previous section has no end point")
            actual_start_z = user_start_z
        
        # MODULO CALCULATION for perfect gap-free alignment
        # Formula from planofaction.md:
        # calculated_layer_height_0_for_b = section_A_calculated_transition_z % layer_height_b
        adjusted_initial = actual_start_z % layer_height
        
        # Handle edge cases
        adjusted_initial = round(adjusted_initial, 6)  # Avoid floating point errors
        if adjusted_initial < 0.001:
            # Very small value means we're aligned on a layer boundary
            adjusted_initial = layer_height
        
        # Validate adjusted initial is reasonable
        if adjusted_initial <= 0 or adjusted_initial > layer_height:
            Logger.log("w", f"Section {section_num}: Invalid adjusted_initial {adjusted_initial:.6f}, using original")
            adjusted_initial = original_initial
            alignment_type = 'fallback_invalid_modulo'
        else:
            alignment_type = 'modulo_match'
        
        # Calculate where this section ends (if it has an end boundary)
        actual_end_z = None
        end_layer_num = None
        total_layers = None
        
        if user_end_z is not None:
            # Generate layer boundaries to find where pattern actually ends
            # CRITICAL: adjusted_initial is just a buffer for calculations, NOT a physical layer
            # All layers in following sections use layer_height!
            layer_boundaries = []
            current_z = actual_start_z + layer_height  # First ACTUAL layer uses layer_height
            layer_num = 1
            
            # Generate enough layers to cover the range
            while current_z <= user_end_z + layer_height:
                layer_boundaries.append((layer_num, round(current_z, 6)))
                current_z += layer_height
                layer_num += 1
            
            # Find last layer within tolerance of user boundary
            tolerance = layer_height
            valid_boundaries = [
                (ln, z) for ln, z in layer_boundaries 
                if z <= user_end_z + tolerance
            ]
            
            if valid_boundaries:
                end_layer_num, actual_end_z = valid_boundaries[-1]
                total_layers = end_layer_num
            else:
                Logger.log("w", f"Section {section_num}: No valid end boundary found")
                actual_end_z = user_end_z
                end_layer_num = 0
        
        # Calculate gap and deviation
        gap = actual_start_z - prev_transition.actual_end_z if prev_transition.actual_end_z else 0.0
        deviation_start = abs(actual_start_z - user_start_z)
        deviation_end = abs(actual_end_z - user_end_z) if actual_end_z and user_end_z else 0.0
        deviation = max(deviation_start, deviation_end)
        
        return TransitionData(
            section_num=section_num,
            profile_id=params['profile_id'],
            profile_name=params.get('profile_name'),
            user_start_z=user_start_z,
            user_end_z=user_end_z,
            actual_start_z=actual_start_z,
            actual_end_z=actual_end_z,
            layer_height=layer_height,
            original_initial_layer_height=original_initial,
            adjusted_initial_layer_height=adjusted_initial,
            material_shrinkage_percentage_z=params.get('material_shrinkage_percentage_z', 100.0),
            start_layer_num=None,  # Will be calculated relative to section start
            end_layer_num=end_layer_num,
            total_layers=total_layers,
            retraction_enabled=params.get('retraction_enabled', True),
            retraction_amount=params.get('retraction_amount', 2.0),
            retraction_speed=params.get('retraction_speed', 35.0),
            prime_speed=params.get('prime_speed', 30.0),
            alignment_type=alignment_type,
            gap_with_previous=gap,
            deviation_from_user=deviation
        )
    
    def _validate_all_transitions(self):
        """Validate all calculated transitions for consistency and physical validity."""
        self._validation_errors = []
        
        # Validate each transition individually
        for transition in self._transitions:
            is_valid, errors = transition.validate()
            if not is_valid:
                self._validation_errors.extend(errors)
        
        # Validate relationships between transitions
        for i in range(len(self._transitions) - 1):
            current = self._transitions[i]
            next_trans = self._transitions[i + 1]
            
            # Check continuity: next section must start where current ends
            if current.actual_end_z is not None:
                gap = abs(next_trans.actual_start_z - current.actual_end_z)
                if gap > 0.01:  # More than 10 microns
                    self._validation_errors.append(
                        f"Gap between Section {current.section_num} and {next_trans.section_num}: {gap:.3f}mm"
                    )
                
                # Check overlap
                if next_trans.actual_start_z < current.actual_end_z - 0.001:
                    self._validation_errors.append(
                        f"Overlap between Section {current.section_num} and {next_trans.section_num}"
                    )
    
    def get_transitions(self) -> List[TransitionData]:
        """Get the calculated transitions."""
        return self._transitions
    
    def get_validation_errors(self) -> List[str]:
        """Get any validation errors."""
        return self._validation_errors
    
    def has_errors(self) -> bool:
        """Check if there are any validation errors."""
        return len(self._validation_errors) > 0
    
    def get_summary(self) -> str:
        """Get human-readable summary of all transitions."""
        lines = []
        lines.append("=" * 60)
        lines.append("TRANSITION CALCULATION SUMMARY")
        lines.append("=" * 60)
        
        for transition in self._transitions:
            lines.append("")
            lines.append(transition.get_summary())
        
        if self._validation_errors:
            lines.append("")
            lines.append("=" * 60)
            lines.append("VALIDATION ERRORS")
            lines.append("=" * 60)
            for error in self._validation_errors:
                lines.append(f"  ⚠️  {error}")
        else:
            lines.append("")
            lines.append("✓ All transitions validated successfully")
        
        lines.append("=" * 60)
        return "\n".join(lines)
