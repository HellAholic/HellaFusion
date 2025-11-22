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
from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices

from UM.Extension import Extension
from UM.Message import Message
from UM.Logger import Logger

from .HellaFusionDialog import HellaFusionDialog
from .HellaFusionJob import HellaFusionJob


class HellaFusion(Extension):
    """Main extension class for the HellaFusion plugin."""
    
    def __init__(self):
        super().__init__()
        self.addMenuItem("HellaFusion", self.showDialog)
        
        # Plugin state
        self._dialog = None
        self._job = None
        self._message = None
        
    def showDialog(self):
        """Show the HellaFusion configuration dialog."""
        if self._dialog is None:
            self._dialog = HellaFusionDialog()
            self._dialog.startProcessing.connect(self.startSplicing)
            self._dialog.stopProcessing.connect(self.stopSplicing)
        
        self._dialog.show()
        self._dialog.raise_()
    
    def startSplicing(self, destination_folder, transitions, slice_timeout, calculated_transitions=None):
        """Start the gcode splicing process.
        
        Args:
            destination_folder: Where to save the output gcode
            transitions: List of transition definitions with heights and profiles
            slice_timeout: Timeout for each slicing operation
            calculated_transitions: Optional list of calculated initial layer height adjustments
        """
        if self._job and self._job.isRunning():
            Logger.log("w", "Cannot start gcode splicing - job already running")
            return

        try:
            # Create the splicing job (uses model on build plate)  
            self._job = HellaFusionJob(destination_folder, transitions, slice_timeout, calculated_transitions)
            self._job.progress.connect(self._onProgress)
            self._job.finished.connect(self._onJobCompleted)
            self._job.statusChanged.connect(self._onJobStatusChanged)
            
            # Start the job - it will handle its own state transitions
            self._job.start()
            
            # Show progress message
            self._message = Message(
                title="HellaFusion", 
                text="Starting gcode splicing process...", 
                lifetime=0, 
                dismissable=False, 
                progress=-1
            )
            self._message.show()
            
        except Exception as e:
            Logger.logException("e", f"Failed to start gcode splicing: {str(e)}")
            if self._dialog:
                self._dialog.onProcessingError(f"Failed to start: {str(e)}")
    
    def stopSplicing(self):
        """Stop the gcode splicing process gracefully."""
        if not self._job or not self._job.isRunning():
            Logger.log("w", "No gcode splicing process is running")
            return
        
        try:
            if self._job:
                self._job.stop()
            
            if self._message:
                self._message.hide()
                
        except Exception as e:
            Logger.logException("e", f"Error stopping gcode splicing: {str(e)}")
    
    def _onProgress(self, progress):
        """Handle progress updates from the job."""
        if self._message:
            self._message.setProgress(progress)
        
        if self._dialog:
            self._dialog.onProgressUpdate(progress)
    
    def _onJobStatusChanged(self, status_info):
        """Handle status updates from the job."""
        # Handle both string and dict status updates for better error handling
        if isinstance(status_info, dict):
            status_text = status_info.get('message', 'Processing...')
            status_type = status_info.get('status', 'info')
            exception = status_info.get('exception')
            
            if self._message:
                self._message.setText(status_text)
            
            if self._dialog:
                if status_type == 'error' and exception:
                    self._dialog.onProcessingError(status_text, exception)
                else:
                    self._dialog.onStatusUpdate(status_text)
        else:
            # Backwards compatibility for string status
            if self._message:
                self._message.setText(status_info)
            
            if self._dialog:
                self._dialog.onStatusUpdate(status_info)
    
    def _onJobCompleted(self, job):
        """Handle job completion."""        
        if self._message:
            self._message.hide()
        
        try:
            # Get results from job
            results = job.getResult()
            success = results.get('success', False)
            output_file = results.get('output_file', '')
            error_message = results.get('error_message', '')
            
            # Show completion message
            if success:
                completion_message = Message(
                    title="HellaFusion Complete",
                    text=f"Successfully created fused gcode file:\n{output_file}",
                    message_type=Message.MessageType.POSITIVE
                )
                # Add "Open Folder" action button
                completion_message.addAction("open_folder", "Open Folder", "open-folder", "Open the folder containing the file")
                completion_message._folder = os.path.dirname(output_file)
                completion_message.actionTriggered.connect(self._onMessageActionTriggered)
                completion_message.show()
            else:
                completion_message = Message(
                    title="HellaFusion Failed",
                    text=f"Failed to create fused gcode:\n{error_message}",
                    message_type=Message.MessageType.ERROR
                )
                completion_message.show()
            
            if self._dialog:
                self._dialog.onProcessingComplete(results)
                
        except Exception as e:
            Logger.logException("e", f"Error handling job completion: {str(e)}")
            if self._dialog:
                self._dialog.onProcessingError(f"Error completing job: {str(e)}")
    
    def _onMessageActionTriggered(self, message, action):
        """Handle action button clicks on messages."""
        if action == "open_folder" and hasattr(message, "_folder"):
            QDesktopServices.openUrl(QUrl.fromLocalFile(message._folder))
    
    @property
    def isRunning(self):
        """Check if gcode splicing is currently running."""
        return self._job is not None and self._job.isRunning()
