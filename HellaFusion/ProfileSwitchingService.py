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

import time
from typing import Optional, Tuple

from UM.Logger import Logger
from cura.CuraApplication import CuraApplication
from cura.Machines.ContainerTree import ContainerTree

from .PluginConstants import PluginConstants
from .HellaFusionExceptions import ProfileSwitchError


class ProfileSwitchingService:
    """Centralized service for handling quality profile switching operations."""
    
    def __init__(self):
        self._application = CuraApplication.getInstance()
        self._machine_manager = self._application.getMachineManager()
        self._container_registry = self._application.getContainerRegistry()
        
    def switch_to_profile(self, profile_id: str, intent_category: Optional[str] = None, 
                         intent_container_id: Optional[str] = None) -> bool:
        """
        Switch to the specified quality profile.
        
        Args:
            profile_id: ID of the quality profile container
            intent_category: Optional intent category 
            intent_container_id: Optional specific intent container ID
            
        Returns:
            True if switch was successful, False otherwise
            
        Raises:
            ProfileSwitchError: If profile switching fails
        """
        try:            
            if not self._machine_manager:
                raise ProfileSwitchError("No machine manager available")
            
            # Check if it's a quality_changes (custom profile)
            quality_changes_containers = self._container_registry.findInstanceContainers(
                type="quality_changes", id=profile_id
            )
            
            if quality_changes_containers:
                success = self._switch_to_quality_changes(quality_changes_containers[0])
            else:
                # Base quality profile
                quality_containers = self._container_registry.findInstanceContainers(
                    type="quality", id=profile_id
                )
                if quality_containers:
                    success = self._switch_to_quality(quality_containers[0])
                else:
                    raise ProfileSwitchError(f"Profile not found: {profile_id}", profile_id)
            
            if not success:
                raise ProfileSwitchError(f"Failed to switch to profile {profile_id}", profile_id)
            
            # Set intent if specified
            if intent_category:
                self._set_intent_category(intent_category)
            
            # Allow time for Cura to process changes
            time.sleep(PluginConstants.BACKEND_SETTLING_TIME)
            
            return True
                
        except ProfileSwitchError:
            raise
        except Exception as e:
            error_msg = f"Error switching quality profile: {str(e)}"
            Logger.logException("e", error_msg)
            raise ProfileSwitchError(error_msg)
    
    def _switch_to_quality_changes(self, quality_changes_container) -> bool:
        """Switch to a quality_changes (custom) profile."""
        try:
            # Try using ContainerTree approach first
            container_tree = ContainerTree.getInstance()
            quality_changes_groups = container_tree.getCurrentQualityChangesGroups()
            
            target_group = None
            for group in quality_changes_groups:
                if hasattr(group, 'name') and group.name == quality_changes_container.getName():
                    target_group = group
                    break
            
            if target_group:
                self._machine_manager.setQualityChangesGroup(target_group, no_dialog=True)
                return True
            else:
                # Fallback to direct container assignment
                active_machine = self._machine_manager.activeMachine
                if active_machine:
                    active_machine.setQualityChanges(quality_changes_container)
                    return True
                else:
                    Logger.log("e", "No active machine available for quality changes switch")
                    return False
                    
        except Exception as e:
            Logger.log("e", f"Error switching to quality changes: {e}")
            return False
    
    def _switch_to_quality(self, quality_container) -> bool:
        """Switch to a base quality profile."""
        try:
            # Try using ContainerTree approach first
            container_tree = ContainerTree.getInstance()
            quality_groups = container_tree.getCurrentQualityGroups()
            
            target_group = None
            quality_type = quality_container.getMetaDataEntry("quality_type")
            
            for group_name, group in quality_groups.items():
                if hasattr(group, 'quality_type') and group.quality_type == quality_type:
                    target_group = group
                    break
            
            if target_group:
                self._machine_manager.setQualityGroup(target_group, no_dialog=True, global_stack=None)
                return True
            else:
                # Fallback to direct container assignment
                active_machine = self._machine_manager.activeMachine
                if active_machine:
                    active_machine.setQuality(quality_container)
                    
                    # Clear quality_changes to avoid conflicts
                    empty_quality_changes = self._container_registry.findInstanceContainers(
                        type="quality_changes", name="empty"
                    )
                    if empty_quality_changes:
                        active_machine.setQualityChanges(empty_quality_changes[0])
                    
                    return True
                else:
                    Logger.log("e", "No active machine available for quality switch")
                    return False
                    
        except Exception as e:
            Logger.log("e", f"Error switching to quality: {e}")
            return False
    
    def _set_intent_category(self, intent_category: str):
        """Set the intent category."""
        try:
            if intent_category and intent_category.lower() not in ["", "default", "none"]:
                self._machine_manager.setIntentByCategory(intent_category)
        except Exception as e:
            Logger.log("w", f"Failed to set intent {intent_category}: {e}")
    
    def get_current_profile_info(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get information about the currently active profile.
        
        Returns:
            Tuple of (quality_id, quality_changes_id, intent_category)
        """
        try:
            active_machine = self._machine_manager.activeMachine
            if not active_machine:
                return None, None, None
            
            quality_id = active_machine.quality.getId() if active_machine.quality else None
            quality_changes_id = active_machine.qualityChanges.getId() if active_machine.qualityChanges else None
            intent_category = self._machine_manager.activeIntentCategory
            
            return quality_id, quality_changes_id, intent_category
            
        except Exception as e:
            Logger.log("e", f"Error getting current profile info: {e}")
            return None, None, None
    
    def backup_current_state(self) -> dict:
        """
        Backup the current machine state for later restoration.
        
        Returns:
            Dictionary containing current state information
        """
        try:
            quality_id, quality_changes_id, intent_category = self.get_current_profile_info()
            
            backup = {
                'quality_id': quality_id,
                'quality_changes_id': quality_changes_id,
                'intent_category': intent_category,
                'timestamp': time.time()
            }
            
            return backup
            
        except Exception as e:
            Logger.log("e", f"Error backing up machine state: {e}")
            return {}
    
    def restore_state(self, backup_state: dict) -> bool:
        """
        Restore machine state from backup.
        
        Args:
            backup_state: Dictionary containing backed up state
            
        Returns:
            True if restoration was successful
        """
        try:
            if not backup_state:
                Logger.log("w", "No backup state to restore")
                return False
            
            quality_id = backup_state.get('quality_id')
            quality_changes_id = backup_state.get('quality_changes_id')
            intent_category = backup_state.get('intent_category')
            
            # Restore quality_changes first if available
            if quality_changes_id and quality_changes_id.lower() not in ["empty", "not_supported", "none"]:
                success = self.switch_to_profile(quality_changes_id, intent_category)
                if success:
                    return True
            
            # Otherwise restore base quality
            if quality_id and quality_id.lower() not in ["empty", "not_supported", "none"]:
                success = self.switch_to_profile(quality_id, intent_category)
                if success:
                    return True
            
            Logger.log("w", "No valid profile to restore")
            return False
            
        except Exception as e:
            Logger.log("e", f"Error restoring machine state: {e}")
            return False
