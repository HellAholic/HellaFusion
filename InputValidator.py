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
from typing import List, Dict, Any, Optional, Tuple

from UM.Logger import Logger
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from cura.CuraApplication import CuraApplication

from .PluginConstants import PluginConstants
from .HellaFusionExceptions import ValidationError


class InputValidator:
    """Utility class for validating user inputs and system state."""
    
    @staticmethod
    def validate_destination_folder(folder_path: str) -> List[str]:
        """
        Validate destination folder path.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not folder_path or not folder_path.strip():
            errors.append("Please select a destination folder")
            return errors
        
        folder_path = folder_path.strip()
        
        if not os.path.exists(folder_path):
            errors.append(f"Destination folder does not exist: {folder_path}")
        elif not os.path.isdir(folder_path):
            errors.append(f"Path is not a directory: {folder_path}")
        else:
            # Check if writable
            try:
                test_file = os.path.join(folder_path, "test_write_permission.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception:
                errors.append(f"Destination folder is not writable: {folder_path}")
        
        return errors
    
    @staticmethod
    def validate_model_on_build_plate() -> List[str]:
        """
        Validate that a model exists on the build plate.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        try:
            application = CuraApplication.getInstance()
            scene = application.getController().getScene()
            nodes = [node for node in DepthFirstIterator(scene.getRoot()) if node.getMeshData()]
            
            if not nodes:
                errors.append("No model on build plate. Please load a model first.")
            else:
                # Check if model has reasonable height
                for node in nodes:
                    mesh_data = node.getMeshData()
                    if mesh_data:
                        bounds = mesh_data.getExtents()
                        if bounds:
                            height = bounds.depth  # Z dimension
                            if height < PluginConstants.MIN_MODEL_HEIGHT:
                                errors.append(f"Model height ({height:.2f}mm) is too small (minimum {PluginConstants.MIN_MODEL_HEIGHT}mm)")
                        break
                        
        except Exception as e:
            Logger.log("e", f"Error checking for model: {e}")
            errors.append("Error checking for model on build plate")
        
        return errors
    
    @staticmethod
    def validate_transitions(transitions: List[Dict[str, Any]]) -> List[str]:
        """
        Validate transition definitions.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not transitions:
            errors.append("Please add at least one transition")
            return errors
        
        if len(transitions) > PluginConstants.MAX_TRANSITIONS:
            errors.append(f"Too many transitions (maximum {PluginConstants.MAX_TRANSITIONS} allowed)")
        
        # Validate individual transitions
        previous_height = 0.0
        for i, transition in enumerate(transitions):
            section_num = i + 1
            
            # Check required fields
            if 'start_height' not in transition:
                errors.append(f"Section {section_num}: Missing start height")
                continue
            if 'end_height' not in transition:
                errors.append(f"Section {section_num}: Missing end height")
                continue
            if 'profile_id' not in transition:
                errors.append(f"Section {section_num}: Missing profile selection")
                continue
            
            start_height = transition['start_height']
            end_height = transition['end_height']
            profile_id = transition['profile_id']
            
            # Validate heights
            try:
                start_height = float(start_height)
                end_height = float(end_height) if end_height is not None else None
            except (ValueError, TypeError):
                errors.append(f"Section {section_num}: Invalid height values")
                continue
            
            # Check height ordering
            if start_height <= previous_height and section_num > 1:
                errors.append(f"Section {section_num}: Start height ({start_height}mm) must be greater than previous section end ({previous_height}mm)")
            
            if end_height is not None and end_height <= start_height:
                errors.append(f"Section {section_num}: End height ({end_height}mm) must be greater than start height ({start_height}mm)")
            
            # Validate profile
            if not profile_id or profile_id.strip() == "":
                errors.append(f"Section {section_num}: Please select a quality profile")
            
            previous_height = end_height if end_height is not None else start_height
        
        return errors
    
    @staticmethod
    def validate_quality_profiles(quality_profiles: List[Dict[str, Any]]) -> List[str]:
        """
        Validate quality profiles are available.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        if not quality_profiles:
            errors.append("No quality profiles available. Please wait for profiles to load or check your printer configuration.")
        
        return errors
    
    @staticmethod
    def validate_slice_timeout(timeout_value: Any) -> List[str]:
        """
        Validate slice timeout value.
        
        Returns:
            List of error messages (empty if valid)
        """
        errors = []
        
        try:
            timeout = int(timeout_value)
            if timeout < 30:
                errors.append("Slice timeout must be at least 30 seconds")
            elif timeout > 3600:
                errors.append("Slice timeout cannot exceed 3600 seconds (1 hour)")
        except (ValueError, TypeError):
            errors.append("Slice timeout must be a valid number")
        
        return errors
    
    @staticmethod
    def validate_all_inputs(destination_folder: str, transitions: List[Dict[str, Any]], 
                          quality_profiles: List[Dict[str, Any]], slice_timeout: Any) -> List[str]:
        """
        Validate all inputs for starting the splicing process.
        
        Returns:
            List of all validation error messages
        """
        all_errors = []
        
        all_errors.extend(InputValidator.validate_destination_folder(destination_folder))
        all_errors.extend(InputValidator.validate_model_on_build_plate())
        all_errors.extend(InputValidator.validate_transitions(transitions))
        all_errors.extend(InputValidator.validate_quality_profiles(quality_profiles))
        all_errors.extend(InputValidator.validate_slice_timeout(slice_timeout))
        
        return all_errors
    
    @staticmethod
    def get_model_height_info() -> Optional[Tuple[float, str]]:
        """
        Get model height information for validation.
        
        Returns:
            Tuple of (height, model_name) or None if no model found
        """
        try:
            application = CuraApplication.getInstance()
            scene = application.getController().getScene()
            nodes = [node for node in DepthFirstIterator(scene.getRoot()) if node.getMeshData()]
            
            if nodes:
                node = nodes[0]  # Get first model
                mesh_data = node.getMeshData()
                if mesh_data:
                    bounds = mesh_data.getExtents() 
                    if bounds:
                        height = bounds.depth  # Z dimension
                        model_name = node.getName() or "Unknown Model"
                        return height, model_name
            
            return None
            
        except Exception as e:
            Logger.log("e", f"Error getting model height info: {e}")
            return None
