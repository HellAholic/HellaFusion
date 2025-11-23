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

from threading import Lock
from typing import Optional

from UM.Logger import Logger
from .HellaFusionExceptions import StateTransitionError
from .JobState import JobState


class JobStateManager:
    """Thread-safe state management for HellaFusion jobs."""
    
    # Valid state transitions
    _VALID_TRANSITIONS = {
        JobState.IDLE: [JobState.INITIALIZING, JobState.RUNNING, JobState.FAILED],
        JobState.INITIALIZING: [JobState.RUNNING, JobState.FAILED],
        JobState.RUNNING: [JobState.STOPPING, JobState.COMPLETED, JobState.FAILED],
        JobState.STOPPING: [JobState.COMPLETED, JobState.FAILED],
        JobState.COMPLETED: [JobState.IDLE],
        JobState.FAILED: [JobState.IDLE]
    }
    
    def __init__(self):
        self._state = JobState.IDLE
        self._lock = Lock()
        self._error_message: Optional[str] = None
    
    @property
    def current_state(self) -> JobState:
        """Get the current state (thread-safe)."""
        with self._lock:
            return self._state
    
    @property
    def is_running(self) -> bool:
        """Check if job is in a running state."""
        return self.current_state in [JobState.INITIALIZING, JobState.RUNNING, JobState.STOPPING]
    
    @property
    def can_start(self) -> bool:
        """Check if job can be started."""
        return self.current_state == JobState.IDLE
    
    @property
    def error_message(self) -> Optional[str]:
        """Get the current error message."""
        with self._lock:
            return self._error_message
    
    def transition_to(self, new_state: JobState, error_message: Optional[str] = None) -> bool:
        """
        Attempt to transition to a new state.
        
        Args:
            new_state: Target state
            error_message: Optional error message for failed states
            
        Returns:
            True if transition was successful, False otherwise
            
        Raises:
            StateTransitionError: If transition is invalid
        """
        with self._lock:
            current = self._state
            
            # Check if transition is valid
            if new_state not in self._VALID_TRANSITIONS.get(current, []):
                error_msg = f"Invalid state transition from {current.value} to {new_state.value}"
                Logger.log("e", error_msg)
                raise StateTransitionError(error_msg)
            
            # Update state
            old_state = self._state
            self._state = new_state
            
            # Update error message for failed states
            if new_state == JobState.FAILED:
                self._error_message = error_message or "Unknown error"
            elif new_state == JobState.IDLE:
                self._error_message = None
            
            return True
    
    def reset(self):
        """Reset to idle state."""
        with self._lock:
            self._state = JobState.IDLE
            self._error_message = None
