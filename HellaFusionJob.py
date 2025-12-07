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

from UM.Backend.Backend import BackendState
from UM.Job import Job
from UM.Logger import Logger
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Signal import Signal
from UM.Application import Application
from UM.FileHandler.WriteFileJob import WriteFileJob
from UM.FileHandler.FileWriter import FileWriter

from cura.CuraApplication import CuraApplication

from .HellaFusionLogic import HellaFusionLogic
from .PluginConstants import PluginConstants
from .HellaFusionExceptions import (ProfileSwitchError, BackendError)
from .JobStateManager import JobStateManager
from .JobState import JobState
from .ProfileSwitchingService import ProfileSwitchingService

import time
import os
import tempfile
from datetime import datetime
from typing import Dict, Any


class HellaFusionJob(Job):
    """Background job for processing a model with multiple quality profiles and combining gcode."""
    
    statusChanged = Signal()
    
    def __init__(self, destination_folder: str, transitions: list, slice_timeout: int = 300, calculated_transitions: list = None, settings_dict: dict = None) -> None:
        super().__init__()
        
        self._destination_folder = destination_folder
        self._transitions = transitions
        self._slice_timeout = slice_timeout
        self._calculated_transitions = calculated_transitions or []
        
        # Store settings with defaults from PluginConstants if not provided
        self._settings = settings_dict or {}
        self._expert_settings_enabled = self._settings.get('expert_settings_enabled', False)
        self._remove_temp_files = self._settings.get('remove_temp_files', PluginConstants.REMOVE_TEMP_FILES)
        self._temp_file_prefix = self._settings.get('temp_file_prefix', PluginConstants.TEMP_FILE_PREFIX)
        self._output_file_suffix = self._settings.get('output_file_suffix', PluginConstants.OUTPUT_FILE_SUFFIX)
        
        # State management
        self._state_manager = JobStateManager()
        self._current_progress = 0
        self._is_stopping = False
        self._temp_gcode_files = []
        
        # Backend management
        self._backend_state = BackendState.NotStarted
        self._application = CuraApplication.getInstance()
        self._machine_manager = self._application.getMachineManager()
        self._backend = self._application.getBackend()
        
        # Logic instance for retraction settings capture
        self._logic = HellaFusionLogic()
        
        # Signal connections (will be tracked for cleanup)
        self._signal_connections = []
        self._connectBackendSignals()
        
        # Profile switching service
        self._profile_service = ProfileSwitchingService()
        self._original_machine_state = None
        
        # Error tracking
        self._last_backend_error = None
        
        # Results
        self._results = {
            'success': False,
            'output_file': '',
            'error_message': ''
        }
    
    def _connectBackendSignals(self):
        """Connect to backend signals and track connections for cleanup."""
        try:
            # Connect signals and store connections for later cleanup
            connection1 = self._backend.backendStateChange.connect(self._onBackendStateChange)
            connection2 = self._backend.backendError.connect(self._onBackendError)
            
            self._signal_connections.extend([connection1, connection2])
            
        except Exception as e:
            Logger.log("e", f"Failed to connect backend signals: {e}")
            raise BackendError(f"Failed to connect backend signals: {e}")
    
    def _disconnectBackendSignals(self):
        """Disconnect all signal connections."""
        errors = []
        
        for connection in self._signal_connections:
            try:
                if connection:
                    connection.disconnect()
            except Exception as e:
                errors.append(f"Signal disconnect failed: {e}")
        
        self._signal_connections.clear()
        
        if errors:
            Logger.log("w", f"Signal disconnection completed with errors: {'; '.join(errors)}")
    
    def _onBackendStateChange(self, state):
        """Track backend state changes."""
        self._backend_state = state
    
    def _onBackendError(self, error_code):
        """Capture backend errors during slicing."""
        self._last_backend_error = error_code
        Logger.log("e", f"Backend error captured: {error_code}")
    
    def stop(self):
        """Stop the processing job gracefully."""
        try:
            # Update state
            if self._state_manager.current_state in [JobState.RUNNING, JobState.INITIALIZING]:
                self._state_manager.transition_to(JobState.STOPPING)
            
            self._is_stopping = True
            
            # Stop backend slicing if in progress
            try:
                backend = self._application.getBackend()
                if self._backend_state in [BackendState.Processing, BackendState.NotStarted]:
                    backend.stopSlicing()
            except Exception as e:
                Logger.log("w", f"Error stopping backend slice: {e}")
            
        except Exception as e:
            Logger.log("e", f"Error during job stop: {e}")
            try:
                self._state_manager.transition_to(JobState.FAILED, str(e))
            except:
                pass  # Avoid cascading errors
    
    def run(self) -> None:
        """Main job execution method - uses model already on build plate."""
        try:
            # Transition to running state
            self._state_manager.transition_to(JobState.RUNNING)
            
            self._storeOriginalMachineState()
            
            total_sections = len(self._transitions)
            self.statusChanged.emit(f"Processing {total_sections} sections using model on build plate...")
            
            # Process each section by switching profiles (model already on build plate)
            for index, transition in enumerate(self._transitions):
                if self._is_stopping:
                    self.statusChanged.emit("Processing stopped by user")
                    self._results['error_message'] = "Stopped by user"
                    break
                
                section_num = transition['section_number']
                profile_id = transition['profile_id']
                intent_category = transition.get('intent_category')
                intent_container_id = transition.get('intent_container_id')
                
                progress = int((index / total_sections) * PluginConstants.COMBINING_PROGRESS_START)
                self.progress.emit(progress)
                
                self.statusChanged.emit(f"Processing section {section_num} ({index + 1}/{total_sections})")
                
                # Clear any previous backend errors before processing this section
                self._last_backend_error = None
                
                # Switch to the profile for this section
                if not self._switchQualityProfile(profile_id, intent_category, intent_container_id):
                    error_msg = f"Failed to switch to profile {profile_id} for section {section_num}"
                    Logger.log("e", error_msg)
                    self.statusChanged.emit(f"ERROR: {error_msg}")
                    self._results['error_message'] = error_msg
                    break
                
                # Capture retraction settings from this profile
                retraction_settings = self._logic.get_current_profile_retraction_settings()
                
                # Store the retraction settings for this section
                transition['profile_retraction_settings'] = retraction_settings
                
                # Apply initial layer height adjustment if calculated (let Cura handle the rest)
                if self._calculated_transitions and index < len(self._calculated_transitions):
                    calc_section = self._calculated_transitions[index]
                    adjusted_initial = calc_section.get('adjusted_initial')
                    original_initial = calc_section.get('initial_layer_height')
                    
                    if adjusted_initial is not None:
                        # Always apply the layer height, even if it equals the original
                        # This ensures Cura gets proper signals for settings injection
                        self._applyLayerHeightAdjustment(adjusted_initial)
                    else:
                        self._clearLayerHeightAdjustment()
                else:
                    self._clearLayerHeightAdjustment()
                
                # Get layer height from current profile
                layer_height = PluginConstants.DEFAULT_LAYER_HEIGHT  # Default fallback
                try:
                    from .TransitionData import TransitionData
                    
                    global_stack = self._application.getGlobalContainerStack()
                    if global_stack:
                        # Read raw value from Cura (has shrinkage applied)
                        layer_height_raw = float(global_stack.getProperty("layer_height", "value"))
                        shrinkage_factor = float(global_stack.getProperty("material_shrinkage_percentage_z", "value") or 100.0)
                        
                        # Convert from Cura format to actual value for plugin calculations
                        layer_height = round(TransitionData.convert_from_cura(layer_height_raw, shrinkage_factor), 3)
                except Exception as e:
                    Logger.log("w", f"Could not get layer height from profile: {e}")
                
                # Slice the model with this profile
                gcode_file, error_msg = self._sliceSection(section_num)
                if not gcode_file:
                    detailed_error = f"Failed to slice section {section_num}"
                    if error_msg:
                        detailed_error += f": {error_msg}"
                    Logger.log("e", detailed_error)
                    self.statusChanged.emit(f"ERROR: {detailed_error}")
                    self._results['error_message'] = detailed_error
                    break
                
                # Store adjusted_initial if it was calculated (needed for trimming)
                adjusted_initial_value = None
                original_initial_value = None
                if self._calculated_transitions and index < len(self._calculated_transitions):
                    calc_section = self._calculated_transitions[index]
                    adjusted_initial_value = calc_section.get('adjusted_initial')
                    original_initial_value = calc_section.get('initial_layer_height')
                
                self._temp_gcode_files.append({
                    'section_number': section_num,
                    'file_path': gcode_file,
                    'start_height': transition['start_height'],
                    'end_height': transition['end_height'],
                    'layer_height': layer_height,  # Store layer height from profile
                    'adjusted_initial': adjusted_initial_value,  # Store adjusted initial layer height (for trimming)
                    'original_initial': original_initial_value  # Store original initial layer height
                })
                
                # Step 6: Section completed successfully
                self.statusChanged.emit(f"Section {section_num}: Completed successfully")
            
            if not self._is_stopping and len(self._temp_gcode_files) > 0:
                # Combine all gcode files (even if some sections were skipped)
                self.statusChanged.emit("Combining gcode files...")
                self.progress.emit(PluginConstants.COMBINING_PROGRESS_START)
                
                skipped_count = len(self._transitions) - len(self._temp_gcode_files)
                if skipped_count > 0:
                    warning_msg = f"{skipped_count} section(s) skipped due to transition heights exceeding model height"
                    Logger.log("w", warning_msg)
                    self.statusChanged.emit(f"WARNING: {warning_msg}")
                
                output_file, combine_error = self._combineGcodeFiles()
                if output_file:
                    self._results['success'] = True
                    self._results['output_file'] = output_file
                    if skipped_count > 0:
                        warning_msg = f"Successfully created spliced gcode ({skipped_count} section(s) skipped)"
                        Logger.log("w", f"{skipped_count} section(s) skipped due to transition heights")
                        self.statusChanged.emit(f"WARNING: {warning_msg}")
                    else:
                        self.statusChanged.emit("Successfully created spliced gcode")
                else:
                    error_msg = "Failed to combine gcode files"
                    if combine_error:
                        error_msg += f": {combine_error}"
                    Logger.log("e", error_msg)
                    self.statusChanged.emit(f"ERROR: {error_msg}")
                    self._results['error_message'] = error_msg
            elif len(self._temp_gcode_files) == 0:
                # Provide more specific error message
                if not self._is_stopping:
                    # Check if it's a model height issue
                    global_stack = self._application.getGlobalContainerStack()
                    if global_stack:
                        try:
                            scene_bb = self._application.getController().getScene().getBoundingBox()
                            if scene_bb:
                                model_height = scene_bb.height
                                first_transition = self._transitions[0]['start_height'] if self._transitions else 0
                                
                                if model_height < first_transition:
                                    error_msg = f"Model height ({model_height:.1f}mm) is less than first transition height ({first_transition:.1f}mm)"
                                    self._results['error_message'] = error_msg
                                    self.statusChanged.emit(f"ERROR: {error_msg}")
                                else:
                                    error_msg = "All sections failed to slice - check profile settings and model compatibility"
                                    self._results['error_message'] = error_msg
                                    self.statusChanged.emit(f"ERROR: {error_msg}")
                            else:
                                error_msg = "No valid sections produced - all transition heights may exceed model height"
                                self._results['error_message'] = error_msg
                                self.statusChanged.emit(f"ERROR: {error_msg}")
                        except Exception as e:
                            Logger.log("w", f"Could not determine model height: {e}")
                            error_msg = "No valid sections produced - verify transition heights and model size"
                            self._results['error_message'] = error_msg
                            self.statusChanged.emit(f"ERROR: {error_msg}")
                    else:
                        error_msg = "No valid sections produced - check transition heights and model"
                        self._results['error_message'] = error_msg
                        self.statusChanged.emit(f"ERROR: {error_msg}")
                else:
                    self._results['error_message'] = "Processing stopped by user"
            
            # Restore original machine state
            self.statusChanged.emit("Restoring original machine state...")
            self._restoreOriginalMachineState()
            
            self.progress.emit(PluginConstants.FINAL_PROGRESS)
            
        except Exception as e:
            error_msg = f"Job failed: {str(e)}"
            Logger.log("e", f"HellaFusionJob failed: {str(e)}")
            
            # Emit error with exception object for better UI handling
            self.statusChanged.emit({
                'status': 'error',
                'message': error_msg,
                'exception': e
            })
            self._results['error_message'] = error_msg
            
            # Set failed state
            try:
                self._state_manager.transition_to(JobState.FAILED, error_msg)
            except:
                pass  # Avoid cascading errors
                
            self._restoreOriginalMachineState()
        finally:
            self._cleanup()
    
    def _sliceSection(self, section_number: int) -> tuple:
        """Wait for slice to complete and save gcode (model already on build plate, profile already switched).
        
        Returns:
            tuple: (gcode_file_path, error_message) where gcode_file_path is empty string on failure
        """
        try:
            # Clear previous backend error
            self._last_backend_error = None
            
            # Notify user that slicing has started
            self.statusChanged.emit(f"Slicing section {section_number}...")
            
            # Ensure slicing happens with current profile and settings
            slice_result, error_msg = self._waitForSlice()
            if not slice_result:
                detailed_error = f"Slicing failed"
                if error_msg:
                    detailed_error = error_msg
                elif self._last_backend_error:
                    detailed_error = f"Backend error: {self._last_backend_error}"
                Logger.log("e", f"Failed to slice section {section_number} - {detailed_error}")
                return "", detailed_error
            
            # Save gcode to temporary file
            temp_file = self._saveTemporaryGcode(section_number)
            if not temp_file:
                error_msg = "Failed to save gcode file"
                Logger.log("e", f"Failed to save gcode for section {section_number}")
                return "", error_msg
            
            return temp_file, ""
            
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            Logger.log("e", f"Error slicing section {section_number}: {error_msg}")
            return "", error_msg
    
    def _waitForSlice(self) -> tuple:
        """Wait for slicing to complete by monitoring backend state.
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        try:
            backend = CuraApplication.getInstance().getBackend()
            
            if not backend.hasSlicableObject():
                error_msg = "No sliceable objects found on build plate"
                Logger.log("e", error_msg)
                return False, error_msg
            
            # Trigger slice with current profile and settings
            backend.forceSlice()
            
            # Wait for backend to reach Done state
            timeout_start = time.time()
            seen_processing = False
            
            while True:
                if self._is_stopping:
                    return False, "Slicing stopped by user"
                
                elapsed = time.time() - timeout_start
                
                # Check timeout
                if elapsed > self._slice_timeout:
                    Logger.log("e", f"Slicing timeout after {self._slice_timeout}s")
                    return False, f"Slicing timeout after {self._slice_timeout} seconds"
                
                # Check current backend state
                current_state = self._backend_state
                
                if current_state == BackendState.Processing:
                    seen_processing = True
                elif current_state == BackendState.Done and seen_processing:
                    return True, ""
                elif current_state == BackendState.Disabled and seen_processing:
                    return True, ""
                elif current_state == BackendState.Error:
                    error_msg = "Backend encountered an error during slicing"
                    if self._last_backend_error:
                        error_msg += f": {self._last_backend_error}"
                    Logger.log("e", error_msg)
                    return False, error_msg
                
                # Small delay to prevent busy waiting
                time.sleep(0.1)
                
        except Exception as e:
            error_msg = f"Exception during slice wait: {str(e)}"
            Logger.log("e", error_msg)
            return False, error_msg
    
    def _saveTemporaryGcode(self, section_number: int) -> str:
        """Save the sliced gcode to a temporary file using Cura's output device flow (includes post-processing)."""
        try:
            # Create temporary file path
            temp_dir = tempfile.gettempdir()
            temp_filename = f"hellafusion_section_{section_number}_{int(time.time())}.gcode"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Get the preferred file format (gcode writer)
            application = Application.getInstance()
            mesh_file_handler = application.getMeshFileHandler()
            file_formats = mesh_file_handler.getSupportedFileTypesWrite()
            
            # Find text/x-gcode format
            preferred_format = None
            for fmt in file_formats:
                if fmt["mime_type"] == "text/x-gcode":
                    preferred_format = fmt
                    break
            
            if not preferred_format:
                Logger.log("e", "Could not find gcode writer")
                return ""
            
            writer = mesh_file_handler.getWriterByMimeType(preferred_format["mime_type"])
            if not writer:
                Logger.log("e", "Could not get gcode writer")
                return ""
            
            # Get scene nodes to write
            scene = application.getController().getScene()
            nodes = []
            for node in DepthFirstIterator(scene.getRoot()):
                if node.callDecoration("isSliceable"):
                    nodes.append(node)
            
            if not nodes:
                Logger.log("e", "No sliceable nodes found")
                return ""
            
            # Execute post-processing scripts before writing
            # This is the standard Cura flow - post-processing happens before the writer is called
            try:
                post_processing_plugin = application.getPluginRegistry().getPluginObject("PostProcessingPlugin")
                if post_processing_plugin:
                    # Pass None as the output device since we're not using a real device
                    post_processing_plugin.execute(None)
            except Exception as e:
                Logger.log("w", f"Could not execute post-processing scripts: {str(e)}")
                # Continue - post-processing is optional
            
            # Write gcode to file using Cura's writer
            with open(temp_path, "wt", buffering=1, encoding="utf-8") as stream:
                writer_args = {}
                job = WriteFileJob(writer, stream, nodes, FileWriter.OutputMode.TextMode, writer_args)
                job.setFileName(temp_path)
                
                # Run synchronously
                job.run()
                
                error = job.getError()
                if error:
                    Logger.log("e", f"Error writing gcode for section {section_number}: {error}")
                    return ""
            
            return temp_path
            
        except Exception as e:
            Logger.log("e", f"Error saving temporary gcode: {str(e)}")
            return ""
    
    def _combineGcodeFiles(self) -> tuple:
        """Combine all gcode files using the splicing logic.
        
        Returns:
            tuple: (output_file_path, error_message) where output_file_path is empty string on failure
        """
        try:
            # Get model name from PrintInformation (same as UI display)
            print_info = self._application.getPrintInformation()
            model_name = print_info.jobName if print_info and print_info.jobName else "model"
            
            # Remove file extension if present
            if model_name.lower().endswith(('.stl', '.obj', '.3mf', '.ply', '.gcode')):
                model_name = os.path.splitext(model_name)[0]
            
            # Create output filename using configured suffix
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"{model_name}{self._output_file_suffix}{timestamp}.gcode"
            output_path = os.path.join(self._destination_folder, output_filename)
            
            # Validate output directory
            if not os.path.exists(self._destination_folder):
                error_msg = f"Output folder does not exist: {self._destination_folder}"
                Logger.log("e", error_msg)
                self.statusChanged.emit(f"ERROR: {error_msg}")
                return "", error_msg
            
            if not os.access(self._destination_folder, os.W_OK):
                error_msg = f"Output folder is not writable: {self._destination_folder}"
                Logger.log("e", error_msg)
                self.statusChanged.emit(f"ERROR: {error_msg}")
                return "", error_msg
            
            # Use the existing HellaFusionLogic instance
            
            # Prepare section data for logic
            sections_data = []
            for gcode_info in self._temp_gcode_files:
                # Verify temp file exists before combining
                if not os.path.exists(gcode_info['file_path']):
                    error_msg = f"Temporary gcode file missing for section {gcode_info['section_number']}: {gcode_info['file_path']}"
                    Logger.log("e", error_msg)
                    self.statusChanged.emit(f"ERROR: {error_msg}")
                    return "", error_msg
                
                # Find the corresponding transition to get retraction settings and nozzle height
                retraction_settings = None
                nozzle_height = 0.0
                for transition in self._transitions:
                    if transition['section_number'] == gcode_info['section_number']:
                        retraction_settings = transition.get('profile_retraction_settings')
                        nozzle_height = transition.get('nozzle_height', 0.0)
                        break
                
                section_data = {
                    'section_number': gcode_info['section_number'],
                    'gcode_file': gcode_info['file_path'],
                    'start_height': gcode_info['start_height'],
                    'end_height': gcode_info['end_height'],
                    'layer_height': gcode_info.get('layer_height', 0.2),  # Pass layer height from profile
                    'profile_retraction_settings': retraction_settings,  # Pass retraction settings from profile
                    'adjusted_initial': gcode_info.get('adjusted_initial'),  # Pass adjusted initial layer height
                    'original_initial': gcode_info.get('original_initial'),  # Pass original initial layer height
                    'nozzle_height': nozzle_height  # Pass nozzle height from UI
                }
                sections_data.append(section_data)
            
            # Get pause settings from settings_dict
            pause_data = self._settings.get('transition_pause_data', [])
            
            # Combine gcode files using UNIFIED approach
            success = self._logic.combineGcodeFiles(sections_data, output_path, self._calculated_transitions, self._expert_settings_enabled, pause_data)
            
            if success:
                # Verify output file was created
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    return output_path, ""
                else:
                    error_msg = "Combine reported success but output file was not created"
                    Logger.log("e", error_msg)
                    return "", error_msg
            else:
                error_msg = "HellaFusionLogic.combineGcodeFiles returned False (check logs for details)"
                Logger.log("e", error_msg)
                return "", error_msg
            
        except Exception as e:
            error_msg = f"Exception: {str(e)}"
            Logger.log("e", f"Error combining gcode files: {error_msg}")
            return "", error_msg
    
    def _switchQualityProfile(self, profile_id: str, intent_category: str = None, intent_container_id: str = None) -> bool:
        """Switch to the specified quality profile using the centralized service."""
        try:
            return self._profile_service.switch_to_profile(profile_id, intent_category, intent_container_id)
        except ProfileSwitchError as e:
            Logger.log("e", f"Profile switch failed: {e}")
            return False
        except Exception as e:
            Logger.log("e", f"Unexpected error switching quality profile: {str(e)}")
            return False
    
    def _storeOriginalMachineState(self):
        """Store the original machine state to restore later."""
        try:
            self._original_machine_state = self._profile_service.backup_current_state()
        except Exception as e:
            Logger.log("e", f"Error storing original machine state: {str(e)}")
    
    def _restoreOriginalMachineState(self):
        """Restore the original machine state after processing."""
        try:
            if self._original_machine_state:
                success = self._profile_service.restore_state(self._original_machine_state)
                if success:
                    pass
                else:
                    Logger.log("w", "Failed to restore original machine state")
            else:
                Logger.log("w", "No original machine state to restore")
            
            # Clear any layer height adjustments
            self._clearLayerHeightAdjustment()
                
        except Exception as e:
            Logger.log("e", f"Error restoring original machine state: {str(e)}")
    
    def _cleanup(self):
        """Comprehensive cleanup with error recovery for all resources."""
        cleanup_errors = []
                
        # 1. Disconnect signal connections
        try:
            self._disconnectBackendSignals()
        except Exception as e:
            cleanup_errors.append(f"Signal cleanup failed: {e}")
            Logger.log("w", f"Signal cleanup error: {e}")
        
        # 2. Clean up temporary files
        if self._remove_temp_files:
            files_deleted = 0
            for gcode_info in self._temp_gcode_files:
                try:
                    file_path = gcode_info.get('file_path', '') if isinstance(gcode_info, dict) else str(gcode_info)
                    if file_path and os.path.exists(file_path):
                        os.remove(file_path)
                        files_deleted += 1
                    elif file_path:
                        pass
                except Exception as e:
                    cleanup_errors.append(f"Failed to remove temp file: {e}")
                    Logger.log("w", f"Failed to remove temp file: {e}")
        
        self._temp_gcode_files.clear()
        
        # 3. Restore original machine state
        try:
            self._restoreOriginalMachineState()
        except Exception as e:
            cleanup_errors.append(f"State restoration failed: {e}")
            Logger.log("w", f"Machine state restoration error: {e}")
        
        # 4. Update job state
        try:
            if self._state_manager.current_state not in [JobState.COMPLETED, JobState.FAILED]:
                if cleanup_errors:
                    self._state_manager.transition_to(JobState.FAILED, f"Cleanup completed with {len(cleanup_errors)} errors")
                else:
                    self._state_manager.transition_to(JobState.COMPLETED)
        except Exception as e:
            cleanup_errors.append(f"State update failed: {e}")
            Logger.log("w", f"State update error: {e}")
        
        # 5. Reset internal state
        try:
            self._is_stopping = False
            self._current_progress = 0
            self._last_backend_error = None
        except Exception as e:
            cleanup_errors.append(f"Internal state reset failed: {e}")
        
        # Final cleanup report
        if cleanup_errors:
            error_summary = "; ".join(cleanup_errors)
            Logger.log("w", f"Cleanup completed with {len(cleanup_errors)} errors: {error_summary}")
            return False
        else:
            return True
    
    def _applyLayerHeightAdjustment(self, adjusted_initial_height: float) -> bool:
        """Apply the calculated initial layer height adjustment to the current profile.
        
        Args:
            adjusted_initial_height: The ACTUAL calculated initial layer height (not Cura format)
        """
        try:
            global_stack = self._application.getGlobalContainerStack()
            
            if not global_stack:
                Logger.log("e", "No global stack available for layer height adjustment")
                return False
            
            # Import TransitionData for conversion helpers
            from .TransitionData import TransitionData
            
            # Get shrinkage factor
            shrinkage_factor = float(global_stack.getProperty("material_shrinkage_percentage_z", "value") or 100.0)
            
            # Convert from actual value to Cura format (apply shrinkage compensation)
            adjusted_initial_height_cura = TransitionData.convert_to_cura(
                adjusted_initial_height, 
                shrinkage_factor
            )
            
            # Get the user changes container
            user_changes = global_stack.userChanges
            
            # Always set the property explicitly to ensure Cura gets proper signals
            # This is required even when the value equals the original to trigger
            # proper settings injection and prevent slicing failures
            user_changes.setProperty("layer_height_0", "value", adjusted_initial_height_cura)
            
            # Give Cura time to process the change
            time.sleep(5)
            
            return True
            
        except Exception as e:
            Logger.log("e", f"Error applying layer height adjustment: {e}")
            return False
    
    def _clearLayerHeightAdjustment(self) -> None:
        """Clear any initial layer height adjustments from user changes."""
        try:
            global_stack = self._application.getGlobalContainerStack()
            
            if not global_stack:
                return
            
            user_changes = global_stack.userChanges
            
            # Remove the override
            if user_changes.hasProperty("layer_height_0", "value"):
                user_changes.removeInstance("layer_height_0")
                
        except Exception as e:
            Logger.log("w", f"Error clearing layer height adjustment: {e}")
    
    def getResult(self) -> Dict[str, Any]:
        """Get the processing results."""
        return self._results
