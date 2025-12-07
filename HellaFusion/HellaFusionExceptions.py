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


class HellaFusionException(Exception):
    """Base exception for all HellaFusion operations.
    
    This exception includes user-friendly messages that can be displayed in the UI.
    """
    
    def __init__(self, message: str, user_message: str = None, details: str = None):
        """Initialize exception with both technical and user-friendly messages.
        
        Args:
            message: Technical error message for logging
            user_message: User-friendly message for UI display (optional)
            details: Additional details for troubleshooting (optional)
        """
        super().__init__(message)
        self.user_message = user_message or message
        self.details = details
        
    def get_ui_message(self) -> str:
        """Get the user-friendly message for UI display."""
        return self.user_message
        
    def get_full_message(self) -> str:
        """Get the full message including details."""
        if self.details:
            return f"{self.user_message}\n\nDetails: {self.details}"
        return self.user_message


class ProfileSwitchError(HellaFusionException):
    """Raised when profile switching fails."""
    
    def __init__(self, message: str, profile_name: str = None):
        user_msg = f"Failed to switch to quality profile"
        if profile_name:
            user_msg += f": {profile_name}"
        user_msg += "\n\nThis could be due to:\n• Profile compatibility issues\n• Cura backend not responding\n• Invalid profile selection"
        
        super().__init__(message, user_msg, message)


class SlicingTimeoutError(HellaFusionException):
    """Raised when slicing operation times out."""
    
    def __init__(self, message: str, timeout_seconds: int = None):
        user_msg = "Slicing operation timed out"
        if timeout_seconds:
            user_msg += f" after {timeout_seconds} seconds"
        user_msg += "\n\nSolutions:\n• Increase timeout in Configuration\n• Simplify your model\n• Check if Cura is responding"
        
        super().__init__(message, user_msg, message)


class SlicingError(HellaFusionException):
    """Raised when slicing operation fails."""
    
    def __init__(self, message: str, section_number: int = None):
        user_msg = "Slicing failed"
        if section_number:
            user_msg += f" for section {section_number}"
        user_msg += "\n\nThis could indicate:\n• Invalid model geometry\n• Incompatible quality settings\n• Insufficient memory\n• Cura backend error"
        
        super().__init__(message, user_msg, message)


class BackendError(HellaFusionException):
    """Raised when backend communication fails."""
    
    def __init__(self, message: str):
        user_msg = "Communication with Cura backend failed\n\nSolutions:\n• Restart Cura\n• Check if other slicing operations work\n• Try a simpler model first"
        super().__init__(message, user_msg, message)


class FileProcessingError(HellaFusionException):
    """Raised when file operations fail."""
    
    def __init__(self, message: str, file_path: str = None, operation: str = None):
        user_msg = "File operation failed"
        if operation:
            user_msg += f" during {operation}"
        if file_path:
            user_msg += f"\nFile: {file_path}"
        user_msg += "\n\nSolutions:\n• Check file permissions\n• Ensure sufficient disk space\n• Verify destination folder exists"
        
        super().__init__(message, user_msg, message)


class StateTransitionError(HellaFusionException):
    """Raised when invalid state transitions are attempted."""
    
    def __init__(self, message: str, current_state: str = None, attempted_state: str = None):
        user_msg = "Invalid operation attempted"
        if current_state and attempted_state:
            user_msg += f"\nCannot transition from {current_state} to {attempted_state}"
        user_msg += "\n\nThis is likely a plugin bug. Please report this issue."
        
        super().__init__(message, user_msg, message)


class ResourceCleanupError(HellaFusionException):
    """Raised when resource cleanup fails."""
    
    def __init__(self, message: str):
        user_msg = "Failed to clean up temporary resources\n\nThis may leave temporary files on disk.\nYou can safely ignore this error if the main operation completed successfully."
        super().__init__(message, user_msg, message)


class ValidationError(HellaFusionException):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field_name: str = None):
        user_msg = "Input validation failed"
        if field_name:
            user_msg += f" for {field_name}"
        user_msg += f"\n\n{message}"
        
        super().__init__(message, user_msg, message)
