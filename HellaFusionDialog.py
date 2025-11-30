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
import subprocess
import platform
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QTextEdit, QProgressBar,
                             QFileDialog, QSpinBox, QGroupBox, QGridLayout,
                             QComboBox, QSizePolicy, QWidget, QDoubleSpinBox,
                             QMessageBox, QScrollArea, QTabWidget, QCheckBox)
from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QFont

from UM.Logger import Logger
from cura.CuraApplication import CuraApplication
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator

from .HellaFusionExceptions import (HellaFusionException, ProfileSwitchError,
                                    BackendError, SlicingTimeoutError)
from .PluginConstants import PluginConstants
from .HellaFusionController import HellaFusionController
from .HelpDialog import HelpDialog


class HellaFusionDialog(QDialog):
    """Main dialog for the HellaFusion plugin."""
    
    # Signals
    startProcessing = pyqtSignal(str, list, int, object)  # dest_folder, transitions, timeout, calculated_transitions
    stopProcessing = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HellaFusion")
        self.setMinimumSize(PluginConstants.DIALOG_MIN_WIDTH, PluginConstants.DIALOG_MIN_HEIGHT)
        self.setFixedWidth(PluginConstants.DIALOG_MAX_WIDTH)
        self.resize(PluginConstants.DIALOG_MAX_WIDTH, PluginConstants.DIALOG_MIN_HEIGHT)
        
        self.setStyleSheet(PluginConstants.DIALOG_BACKGROUND_STYLE)
        
        # Initialize controller
        self._controller = HellaFusionController()
        
        # Connect controller signals
        self._controller.qualityProfilesLoaded.connect(self._onQualityProfilesLoaded)
        self._controller.logMessageEmitted.connect(self._logMessage)
        
        # State
        self._is_processing = False
        self._quality_profiles = []
        self._transition_rows = []  # List of transition row widgets
        self._calculated_transitions = None  # Stores calculated transition adjustments
        self._calculation_invalid = False  # Track if calculations need to be refreshed
        
        # Help content
        self.help_content = PluginConstants.HELP_CONTENT
        
        # Flag to prevent saving during initialization
        self._is_loading = True
        
        self._setupUI()
        self._loadSettings()
        
        # Connect to scene changes to update model info
        self._connectSceneSignals()
        
        # Connect existing UI elements to invalidation handlers
        self._connectInvalidationHandlers()
        
        # Initial update of button state (check if models are on build plate)
        self._updateModelInfo()
        
        # Enable saving now that initialization is complete
        self._is_loading = False
        
    def _setupUI(self):
        """Set up the user interface."""
        layout = QVBoxLayout()
        
        # Create tab widget
        self._tab_widget = QTabWidget()
        self._tab_widget.setStyleSheet(PluginConstants.TAB_WIDGET_STYLE)
        self._tab_widget.currentChanged.connect(self._onTabChanged)
        
        # Help button (positioned in tab bar corner)
        self._help_button = QPushButton("?")
        self._help_button.setToolTip("Click for detailed help and documentation")
        self._help_button.setStyleSheet(PluginConstants.HELP_BUTTON_STYLE)
        self._help_button.clicked.connect(self._show_help_dialog)
        self._help_button.setFixedSize(20, 20)
        self._tab_widget.setCornerWidget(self._help_button, Qt.Corner.TopRightCorner)
        
        # ===== TAB 1: Configuration & Control =====
        config_tab = QWidget()
        config_tab_layout = QVBoxLayout()
        
        # Configuration Section
        config_group = QGroupBox("Configuration")
        config_group.setStyleSheet(PluginConstants.GROUPBOX_STYLE)
        config_layout = QGridLayout()
        
        # Model info display (uses model on build plate)
        model_label = QLabel("Model on Build Plate:")
        model_label.setStyleSheet(PluginConstants.LABEL_STYLE)
        config_layout.addWidget(model_label, 0, 0)
        self._model_info_label = QLabel("No model loaded")
        self._model_info_label.setStyleSheet(PluginConstants.LABEL_STYLE_GRAY)
        config_layout.addWidget(self._model_info_label, 0, 1, 1, 2)
        
        # Destination folder selection
        dest_label = QLabel("Destination Folder:")
        dest_label.setStyleSheet(PluginConstants.LABEL_STYLE)
        config_layout.addWidget(dest_label, 1, 0)
        self._dest_folder_edit = QLineEdit()
        self._dest_folder_edit.setPlaceholderText("Select folder for output gcode")
        self._dest_folder_edit.setStyleSheet(PluginConstants.LINE_EDIT_STYLE)
        self._dest_folder_edit.textChanged.connect(self._saveSettings)
        config_layout.addWidget(self._dest_folder_edit, 1, 1)
        
        # Browse and Open Folder buttons
        dest_buttons_layout = QHBoxLayout()
        dest_buttons_layout.setSpacing(5)
        
        self._dest_browse_btn = QPushButton("Browse...")
        self._dest_browse_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._dest_browse_btn.clicked.connect(self._browseDestFolder)
        dest_buttons_layout.addWidget(self._dest_browse_btn)
        
        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._open_folder_btn.setToolTip("Open destination folder in file explorer")
        self._open_folder_btn.clicked.connect(self._openDestFolder)
        dest_buttons_layout.addWidget(self._open_folder_btn)
        
        config_layout.addLayout(dest_buttons_layout, 1, 2)
        
        # Slice timeout
        timeout_label = QLabel("Slice Timeout (seconds):")
        timeout_label.setStyleSheet(PluginConstants.LABEL_STYLE)
        config_layout.addWidget(timeout_label, 2, 0)
        self._slice_timeout_spin = QSpinBox()
        self._slice_timeout_spin.setMinimum(30)
        self._slice_timeout_spin.setMaximum(3600)
        self._slice_timeout_spin.setValue(300)
        self._slice_timeout_spin.setToolTip("Maximum time to wait for each slicing operation")
        self._slice_timeout_spin.setStyleSheet(PluginConstants.SPIN_BOX_STYLE)
        self._slice_timeout_spin.valueChanged.connect(self._saveSettings)
        config_layout.addWidget(self._slice_timeout_spin, 2, 1)
        
        config_group.setLayout(config_layout)
        config_tab_layout.addWidget(config_group)
        
        # Control Section (moved to tab 1)
        control_group = QGroupBox("Control")
        control_group.setStyleSheet(PluginConstants.GROUPBOX_STYLE)
        control_layout = QHBoxLayout()
        
        self._start_btn = QPushButton("Start Fusing")
        self._start_btn.setStyleSheet(PluginConstants.PRIMARY_BUTTON_STYLE)
        self._start_btn.clicked.connect(self._onStartClicked)
        control_layout.addWidget(self._start_btn)
        
        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setStyleSheet(PluginConstants.DANGER_BUTTON_STYLE)
        self._stop_btn.clicked.connect(self._onStopClicked)
        self._stop_btn.setEnabled(False)
        control_layout.addWidget(self._stop_btn)

        self._calculate_transitions_btn = QPushButton("Calculate Transitions")
        self._calculate_transitions_btn.setStyleSheet(PluginConstants.CALCULATE_BUTTON_STYLE)
        self._calculate_transitions_btn.clicked.connect(self._onCalculateTransitionsClicked)
        self._calculate_transitions_btn.setToolTip("Calculate initial layer height adjustments for perfect transition alignment")
        control_layout.addWidget(self._calculate_transitions_btn)
        
        control_group.setLayout(control_layout)
        config_tab_layout.addWidget(control_group)
        
        # Progress Section (moved to tab 1)
        progress_group = QGroupBox("Progress")
        progress_group.setStyleSheet(PluginConstants.GROUPBOX_STYLE)
        progress_group.setMinimumHeight(100)
        progress_group.setMaximumHeight(100)
        progress_layout = QVBoxLayout()
        
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._progress_bar.setFixedHeight(30)
        self._progress_bar.setStyleSheet(PluginConstants.PROGRESS_BAR_STYLE)
        progress_layout.addWidget(self._progress_bar)
        
        self._status_label = QLabel("Ready")
        self._status_label.setFixedHeight(35)
        self._status_label.setStyleSheet(PluginConstants.STATUS_LABEL_STYLE)
        progress_layout.addWidget(self._status_label)
        
        progress_group.setLayout(progress_layout)
        config_tab_layout.addWidget(progress_group)
        
        # Log Section (moved to tab 1)
        log_group = QGroupBox("Processing Log")
        log_group.setStyleSheet(PluginConstants.GROUPBOX_STYLE)
        log_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        log_layout = QVBoxLayout()
        
        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setMinimumHeight(110)
        self._log_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        font = QFont("Consolas", 9)
        self._log_text.setFont(font)
        self._log_text.setStyleSheet(PluginConstants.LOG_STYLE)
        log_layout.addWidget(self._log_text)

        log_group.setLayout(log_layout)
        config_tab_layout.addWidget(log_group)
        
        config_tab_layout.addStretch()
        config_tab.setLayout(config_tab_layout)
        
        # ===== TAB 2: Transitions Section =====
        transitions_tab = QWidget()
        transitions_tab_layout = QVBoxLayout()
        transitions_tab_layout.setContentsMargins(12, 12, 12, 12)  # Add padding to tab content
        
        # Info label
        info_label = QLabel("Define heights where settings should change. Each section can use a different quality profile.")
        info_label.setStyleSheet(PluginConstants.LABEL_STYLE)
        info_label.setWordWrap(True)
        transitions_tab_layout.addWidget(info_label)
        
        # Create scrollable area for transitions
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        scroll_area.setMinimumHeight(340)
        scroll_area.setStyleSheet(PluginConstants.SCROLL_AREA_STYLE)
        
        # Container widget for transitions
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet(PluginConstants.TRANSPARENT_WIDGET_STYLE)
        self._transitions_container = QVBoxLayout(scroll_widget)
        self._transitions_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._transitions_container.setSpacing(8)
        
        scroll_area.setWidget(scroll_widget)
        transitions_tab_layout.addWidget(scroll_area)
        
        # Expert settings checkbox
        expert_settings_layout = QHBoxLayout()
        expert_settings_layout.setContentsMargins(0, 8, 0, 0)
        
        self._expert_settings_checkbox = QCheckBox("Show Expert Settings")
        self._expert_settings_checkbox.setStyleSheet(PluginConstants.CHECKBOX_STYLE)
        self._expert_settings_checkbox.stateChanged.connect(self._onExpertSettingsToggled)
        expert_settings_layout.addWidget(self._expert_settings_checkbox)
        expert_settings_layout.addStretch()
        
        transitions_tab_layout.addLayout(expert_settings_layout)
        
        # Add/Remove buttons
        transition_buttons_layout = QHBoxLayout()
        transition_buttons_layout.setContentsMargins(0, 8, 0, 0)  # Add top margin for spacing
        
        self._add_transition_btn = QPushButton("Add Transition")
        self._add_transition_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._add_transition_btn.setMinimumWidth(140)
        self._add_transition_btn.setFixedHeight(36)
        self._add_transition_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._add_transition_btn.clicked.connect(self._addTransition)
        transition_buttons_layout.addWidget(self._add_transition_btn)
        
        self._remove_transition_btn = QPushButton("Remove Last Transition")
        self._remove_transition_btn.setStyleSheet(PluginConstants.DANGER_BUTTON_STYLE)
        self._remove_transition_btn.setMinimumWidth(200)
        self._remove_transition_btn.setFixedHeight(36)
        self._remove_transition_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._remove_transition_btn.clicked.connect(self._removeLastTransition)
        self._remove_transition_btn.setEnabled(False)
        transition_buttons_layout.addWidget(self._remove_transition_btn)
        
        self._update_profiles_btn = QPushButton("Reload Profiles from Cura")
        self._update_profiles_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._update_profiles_btn.setMinimumWidth(140)
        self._update_profiles_btn.setFixedHeight(36)
        self._update_profiles_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._update_profiles_btn.clicked.connect(self._updateQualityProfiles)
        self._update_profiles_btn.setToolTip("Refresh quality profiles from current Cura settings")
        transition_buttons_layout.addWidget(self._update_profiles_btn)
        
        transition_buttons_layout.addStretch()
        transitions_tab_layout.addLayout(transition_buttons_layout)
        
        # Add first section by default (before setting layout to avoid premature rendering)
        self._addSectionRow(1)
        
        transitions_tab.setLayout(transitions_tab_layout)
        
        # Add tabs to tab widget
        self._tab_widget.addTab(config_tab, "Configuration & Control")
        self._tab_widget.addTab(transitions_tab, "Transitions & Sections")
        
        layout.addWidget(self._tab_widget)
        
        # Bottom buttons
        bottom_layout = QHBoxLayout()

        # Clear log button (left side)
        self._clear_log_btn = QPushButton("Clear Logs")
        self._clear_log_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._clear_log_btn.clicked.connect(self._clearLog)
        bottom_layout.addWidget(self._clear_log_btn)
        
        bottom_layout.addStretch()
        
        self._close_btn = QPushButton("Close")
        self._close_btn.setStyleSheet(PluginConstants.WARNING_BUTTON_STYLE)
        self._close_btn.clicked.connect(self.close)
        bottom_layout.addWidget(self._close_btn)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
    
    def _addSectionRow(self, section_number):
        """Add a section row to the UI."""
        section_widget = QWidget()
        section_layout = QHBoxLayout()
        section_layout.setContentsMargins(0, 5, 0, 5)
        
        # Section label
        section_label = QLabel(f"Section {section_number}:")
        section_label.setStyleSheet(PluginConstants.LABEL_STYLE_SECTION)
        section_layout.addWidget(section_label)
        
        # Profile selector
        profile_combo = QComboBox()
        profile_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        profile_combo.setStyleSheet(PluginConstants.COMBOBOX_STYLE)
        profile_combo.currentIndexChanged.connect(self._onProfileSelectionChanged)
        self._populateProfileCombo(profile_combo)
        section_layout.addWidget(profile_combo)
        
        # Expert settings: Nozzle height for this section
        show_expert = self._expert_settings_checkbox.isChecked()
        
        nozzle_height_label = QLabel(f"Nozzle Height:")
        nozzle_height_label.setStyleSheet(PluginConstants.LABEL_STYLE)
        nozzle_height_label.hide()
        section_layout.addWidget(nozzle_height_label)
        
        nozzle_height_spin = QDoubleSpinBox()
        nozzle_height_spin.setDecimals(2)
        nozzle_height_spin.setMinimum(0.0)
        nozzle_height_spin.setMaximum(20.0)
        nozzle_height_spin.setSingleStep(0.1)
        nozzle_height_spin.setValue(0.0)
        nozzle_height_spin.setStyleSheet(PluginConstants.SPIN_BOX_STYLE)
        nozzle_height_spin.hide()
        section_layout.addWidget(nozzle_height_spin)
        
        section_widget.setLayout(section_layout)
        self._transitions_container.addWidget(section_widget)
        
        # Set suffix and show widgets AFTER being added to parent container
        nozzle_height_spin.setSuffix(" mm")
        if show_expert:
            nozzle_height_label.show()
            nozzle_height_spin.show()
        
        # Store reference
        self._transition_rows.append({
            'section_number': section_number,
            'widget': section_widget,
            'profile_combo': profile_combo,
            'height_spin': None,  # Only transitions have heights
            'nozzle_height_label': nozzle_height_label,
            'nozzle_height_spin': nozzle_height_spin,
            'is_transition': False
        })
    
    def _addTransition(self):
        """Add a new transition height input and create next section."""
        transition_number = len([r for r in self._transition_rows if r['is_transition']]) + 1
        # Count only sections, not transitions
        next_section = len([r for r in self._transition_rows if not r['is_transition']]) + 1
        
        # Add transition row
        transition_widget = QWidget()
        transition_layout = QHBoxLayout()
        transition_layout.setContentsMargins(0, 5, 0, 5)
        
        # Transition label
        transition_label = QLabel(f"↓ Transition at Z:")
        transition_label.setStyleSheet(PluginConstants.LABEL_STYLE_TRANSITION)
        transition_layout.addWidget(transition_label)
        
        # Height input
        height_spin = QDoubleSpinBox()
        height_spin.setMinimum(0.1)
        height_spin.setMaximum(1000.0)
        height_spin.setValue(10.0 * transition_number)
        height_spin.setDecimals(2)
        height_spin.setSuffix(" mm")
        height_spin.setStyleSheet(PluginConstants.SPIN_BOX_STYLE)
        height_spin.valueChanged.connect(self._onTransitionHeightChanged)
        transition_layout.addWidget(height_spin)
        
        transition_layout.addStretch()
        
        transition_widget.setLayout(transition_layout)
        self._transitions_container.addWidget(transition_widget)
        
        # Store transition reference
        self._transition_rows.append({
            'transition_number': transition_number,
            'widget': transition_widget,
            'profile_combo': None,
            'height_spin': height_spin,
            'nozzle_height_label': None,  # Nozzle height is now on sections
            'nozzle_height_spin': None,  # Nozzle height is now on sections
            'is_transition': True
        })
        
        # Add next section
        self._addSectionRow(next_section)
        
        # Enable remove button
        self._remove_transition_btn.setEnabled(True)
        
        # Invalidate calculations since we added a transition
        self._invalidateCalculations()
        self._saveSettings()
    
    def _removeLastTransition(self):
        """Remove the last transition and its following section."""
        if not self._transition_rows:
            return
        
        # Find last transition
        last_transition_idx = None
        for i in range(len(self._transition_rows) - 1, -1, -1):
            if self._transition_rows[i]['is_transition']:
                last_transition_idx = i
                break
        
        if last_transition_idx is None:
            return
        
        # Remove last section (always after last transition)
        last_section = self._transition_rows[-1]
        last_section['widget'].deleteLater()
        self._transition_rows.pop()
        
        # Remove last transition
        transition_row = self._transition_rows[last_transition_idx]
        transition_row['widget'].deleteLater()
        self._transition_rows.pop(last_transition_idx)
        
        # Disable remove button if no transitions left
        has_transitions = any(r['is_transition'] for r in self._transition_rows)
        self._remove_transition_btn.setEnabled(has_transitions)
        
        # Invalidate calculations since we removed a transition
        self._invalidateCalculations()
        self._saveSettings()
    
    def _updateQualityProfiles(self):
        """Update quality profiles from current Cura settings and refresh all profile combos."""
        if not self._controller:
            Logger.log("w", "No controller available for updating quality profiles")
            return
        
        # Temporarily disable the button to prevent multiple clicks
        self._update_profiles_btn.setEnabled(False)
        self._update_profiles_btn.setText("Updating...")
        
        try:
            # Trigger quality profiles reload through controller
            self._logMessage("Updating quality profiles from current Cura settings...")
            self._controller._loadQualityProfilesAsync()
            
            # Give the async operation a moment to complete, then update
            QTimer.singleShot(500, self._finishProfileUpdate)
            
        except Exception as e:
            Logger.log("e", f"Error updating quality profiles: {str(e)}")
            self._logMessage(f"Error updating quality profiles: {str(e)}", is_error=True)
            # Re-enable the button on error
            self._update_profiles_btn.setEnabled(True)
            self._update_profiles_btn.setText("Reload Profiles from Cura")
    
    def _finishProfileUpdate(self):
        """Complete the profile update process."""
        try:
            # Get updated profiles from controller
            self._quality_profiles = self._controller.getQualityProfiles()
            
            # Refresh all profile combo boxes with updated profiles
            for idx, row in enumerate(self._transition_rows):
                if row['profile_combo']:
                    # Store current selection before repopulating
                    current_data = row['profile_combo'].currentData()
                    current_profile_id = None
                    current_intent = None
                    current_quality_name = None
                    
                    # Extract data only if current_data is a valid dict
                    if current_data and isinstance(current_data, dict):
                        current_profile_id = current_data.get('container_id')
                        current_intent = current_data.get('intent_category')
                        current_quality_name = current_data.get('quality_name')
                    
                    # Repopulate combo box without auto-selecting
                    self._populateProfileCombo(row['profile_combo'], auto_select=False)
                    
                    # Try to restore previous selection
                    selection_restored = False
                    if current_profile_id and current_intent:
                        for i in range(row['profile_combo'].count()):
                            item_data = row['profile_combo'].itemData(i)
                            if item_data and isinstance(item_data, dict):
                                # Try exact match first (container_id + intent)
                                if (item_data.get('container_id') == current_profile_id and 
                                    item_data.get('intent_category') == current_intent):
                                    row['profile_combo'].setCurrentIndex(i)
                                    selection_restored = True
                                    break
                    
                    # If exact match failed, try matching by quality name and intent as fallback
                    if not selection_restored and current_quality_name and current_intent:
                        for i in range(row['profile_combo'].count()):
                            item_data = row['profile_combo'].itemData(i)
                            if item_data and isinstance(item_data, dict):
                                if (item_data.get('quality_name') == current_quality_name and 
                                    item_data.get('intent_category') == current_intent):
                                    row['profile_combo'].setCurrentIndex(i)
                                    selection_restored = True
                                    break
                    
                    # If still no match, select first valid item as last resort
                    if not selection_restored:
                        for i in range(row['profile_combo'].count()):
                            model = row['profile_combo'].model()
                            item = model.item(i)
                            if item and item.isEnabled():
                                row['profile_combo'].setCurrentIndex(i)
                                break
            
            self._logMessage(f"Quality profiles updated successfully - {len(self._quality_profiles)} profiles available")
            
            # Invalidate calculations since profile list changed
            self._invalidateCalculations()
            
        except Exception as e:
            Logger.logException("e", f"Error finishing profile update: {str(e)}")
            self._logMessage(f"Error finishing profile update: {str(e)}", is_error=True)
        finally:
            # Re-enable the button
            self._update_profiles_btn.setEnabled(True)
            self._update_profiles_btn.setText("Reload Profiles from Cura")
    
    def _onCalculateTransitionsClicked(self):
        """Handle Calculate Transitions button click."""
        try:
            # Collect transitions (same structure used for slicing)
            transitions = self._collectTransitions()
            
            if not transitions:
                self._logMessage("No transitions defined. Add transitions first.", is_error=True)
                return
            
            self._logMessage("=" * 60)
            self._logMessage("CALCULATING TRANSITION ADJUSTMENTS")
            self._logMessage("=" * 60)
            self._logMessage(f"Processing {len(transitions)} section(s)...")
            
            # Calculate adjustments using controller (which switches profiles to read values)
            try:
                self._calculated_transitions = self._controller.calculateTransitionAdjustments(transitions)
            except Exception as calc_error:
                Logger.log("e", f"Exception during calculation: {str(calc_error)}")
                self._logMessage(f"Calculation error: {str(calc_error)}", is_error=True)
                import traceback
                self._logMessage(traceback.format_exc(), is_error=True)
                return
            
            if not self._calculated_transitions:
                self._logMessage("Calculation failed or returned no results", is_error=True)
                self._logMessage("Check the log for more details", is_error=True)
                return
            
            # Display results
            self._logMessage("")
            self._logMessage("CALCULATION RESULTS:")
            self._logMessage("-" * 60)
            for section in self._calculated_transitions:
                section_num = section['section_num']
                start_z = section['start_z']
                end_z = section['end_z']
                layer_h = section['layer_height']
                initial_h = section['initial_layer_height']
                adjusted_h = section.get('adjusted_initial')
                
                # Check if this is Section 1 (starts at Z=0)
                if start_z == 0.0 and end_z is not None:
                    self._logMessage(f"Section {section_num}: Z={start_z}mm to {end_z}mm (FIRST SECTION)")
                    self._logMessage(f"  Layer height: {layer_h}mm")
                    self._logMessage(f"  Initial layer: {initial_h}mm (build plate adhesion layer)")
                elif end_z is not None:
                    if adjusted_h and abs(adjusted_h - initial_h) > 0.000001:
                        adjustment_diff = adjusted_h - initial_h
                        self._logMessage(f"Section {section_num}: Z={start_z}mm to {end_z}mm")
                        self._logMessage(f"  Layer height: {layer_h}mm")
                        self._logMessage(f"  Initial layer: {initial_h}mm -> {adjusted_h:.6f}mm (Δ {adjustment_diff:+.6f}mm)")
                    else:
                        self._logMessage(f"Section {section_num}: Z={start_z}mm to {end_z}mm")
                        self._logMessage(f"  Layer height: {layer_h}mm")
                        self._logMessage(f"  Initial layer: {initial_h}mm")
                else:
                    # Last section
                    if adjusted_h and abs(adjusted_h - initial_h) > 0.000001:
                        adjustment_diff = adjusted_h - initial_h
                        self._logMessage(f"Section {section_num}: Z={start_z}mm to end (last section)")
                        self._logMessage(f"  Layer height: {layer_h}mm")
                        self._logMessage(f"  Initial layer: {initial_h}mm -> {adjusted_h:.6f}mm (Δ {adjustment_diff:+.6f}mm)")
                    else:
                        self._logMessage(f"Section {section_num}: Z={start_z}mm to end (last section)")
                        self._logMessage(f"  Layer height: {layer_h}mm")
                        self._logMessage(f"  Initial layer: {initial_h}mm")
                self._logMessage("")
            
            self._logMessage("=" * 60)
            self._logMessage("Calculations complete! Profile adjustments have been applied.")
            self._logMessage("=" * 60)
            
            # Mark calculations as valid
            self._calculation_invalid = False
            
        except Exception as e:
            Logger.logException("e", f"Error calculating transitions: {str(e)}")
            self._logMessage(f"Error calculating transitions: {str(e)}", is_error=True)
    
    def _populateProfileCombo(self, combo_box, auto_select=True):
        """Populate a profile combo box with available profiles.
        
        Args:
            combo_box: The QComboBox to populate
            auto_select: If True, automatically select the first valid item. If False, leave selection unchanged.
        """
        combo_box.clear()
        
        if not self._quality_profiles:
            combo_box.addItem("No profiles available")
            combo_box.setEnabled(False)
            return
        
        combo_box.setEnabled(True)
        
        # Group profiles by intent
        intent_groups = {}
        for profile_entry in self._quality_profiles:
            intent = profile_entry['intent']
            intent_display = self._controller.normalizeIntentName(intent)
            if intent_display not in intent_groups:
                intent_groups[intent_display] = []
            intent_groups[intent_display].append(profile_entry)
        
        item_index = 0
        for intent_display in sorted(intent_groups.keys()):
            profiles = intent_groups[intent_display]
            
            # Add header
            header_text = f"── {intent_display} ──"
            combo_box.addItem(header_text)
            model = combo_box.model()
            header_item = model.item(item_index)
            header_item.setEnabled(False)
            item_index += 1
            
            # Add profiles
            for profile_entry in sorted(profiles, key=lambda p: p['quality_name']):
                quality_name = profile_entry['quality_name']
                container = profile_entry['container']
                
                if not container:
                    continue
                
                # Display format: "Quality Name - Intent" (with * for user-defined)
                if profile_entry.get('is_user_defined', False):
                    display_text = f"  * {quality_name} - {intent_display}"
                else:
                    display_text = f"  {quality_name} - {intent_display}"
                
                container_id = container.getId()
                profile_data = {
                    'container_id': container_id,
                    'intent_category': profile_entry['intent'],
                    'intent_container_id': profile_entry.get('intent_container').getId() if profile_entry.get('intent_container') else None,
                    'quality_name': quality_name,
                    'intent_display': intent_display,
                    'quality_type': profile_entry.get('quality_type'),
                    'is_user_defined': profile_entry.get('is_user_defined', False)
                }
                combo_box.addItem(display_text, profile_data)
                item_index += 1
        
        # Only auto-select first valid item if requested
        if auto_select:
            for i in range(combo_box.count()):
                model = combo_box.model()
                item = model.item(i)
                if item and item.isEnabled():
                    combo_box.setCurrentIndex(i)
                    break
    
    def _updateModelInfo(self):
        """Update the model info display using Cura's project name and sliceable objects."""
        try:
            application = CuraApplication.getInstance()
            
            # Get the project name from PrintInformation (includes printer abbreviation)
            print_info = application.getPrintInformation()
            job_name = print_info.jobName if print_info else None
            
            # Get sliceable nodes only (excludes build plate, camera, and other non-printable objects)
            scene = application.getController().getScene()
            sliceable_nodes = [
                node for node in DepthFirstIterator(scene.getRoot()) 
                if node.callDecoration("isSliceable") and node.getMeshData()
            ]
            
            # Check if we have actual printable models
            has_models = len(sliceable_nodes) > 0
            
            if has_models:
                # Use project name if available, otherwise count objects
                if job_name and job_name.strip():
                    self._model_info_label.setText(f"✓ {job_name}")
                    self._model_info_label.setStyleSheet(PluginConstants.LABEL_STYLE_SUCCESS)
                else:
                    # Fallback to object count if no project name
                    object_count = len(sliceable_nodes)
                    if object_count == 1:
                        # Try to get the object name
                        object_name = sliceable_nodes[0].getName()
                        if object_name and object_name.strip():
                            self._model_info_label.setText(f"✓ {object_name}")
                        else:
                            self._model_info_label.setText("✓ 1 object loaded")
                    else:
                        self._model_info_label.setText(f"✓ {object_count} objects loaded")
                    self._model_info_label.setStyleSheet(PluginConstants.LABEL_STYLE_SUCCESS)
            else:
                # No sliceable objects found
                self._model_info_label.setText("⚠ No model on build plate - Please load a model first")
                self._model_info_label.setStyleSheet(PluginConstants.LABEL_STYLE_WARNING)
            
            # Update Start Fusing button state based on model presence
            self._updateStartButtonState(has_models)
            
        except Exception as e:
            Logger.log("w", f"Error updating model info: {e}")
    
    def _updateStartButtonState(self, has_models: bool = None):
        """Update the Start Fusing button enabled state based on build plate status.
        
        Args:
            has_models: Optional bool indicating if models are present. If None, will check.
        """
        try:
            # Check if models are on build plate if not provided
            if has_models is None:
                application = CuraApplication.getInstance()
                scene = application.getController().getScene()
                sliceable_nodes = [
                    node for node in DepthFirstIterator(scene.getRoot()) 
                    if node.callDecoration("isSliceable") and node.getMeshData()
                ]
                has_models = len(sliceable_nodes) > 0
            
            # Enable button only if models are present and not currently processing
            should_enable = has_models and not self._is_processing
            self._start_btn.setEnabled(should_enable)
            
            # Update tooltip to explain why button is disabled
            if not has_models:
                self._start_btn.setToolTip("Please add a model to the build plate before starting")
            elif self._is_processing:
                self._start_btn.setToolTip("Processing in progress...")
            else:
                self._start_btn.setToolTip("Start the gcode fusion process")
                
        except Exception as e:
            Logger.log("w", f"Error updating start button state: {e}")
            self._model_info_label.setText("Error detecting model")
            self._model_info_label.setStyleSheet(PluginConstants.LABEL_STYLE_ERROR)
    
    def _browseDestFolder(self):
        """Browse for destination folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder",
            self._dest_folder_edit.text() or os.path.expanduser("~")
        )
        if folder:
            self._dest_folder_edit.setText(folder)
            self._saveSettings()
    
    def _openDestFolder(self):
        """Open destination folder in native file explorer."""
        folder_path = self._dest_folder_edit.text().strip()
        
        # Check if folder path is set
        if not folder_path:
            QMessageBox.warning(
                self,
                "No Folder Selected",
                "Please select a destination folder first."
            )
            return
        
        # Check if folder exists
        if not os.path.exists(folder_path):
            QMessageBox.warning(
                self,
                "Folder Not Found",
                f"The folder does not exist:\n{folder_path}\n\nPlease select a valid folder."
            )
            return
        
        try:
            # Open folder in native file explorer based on OS
            system = platform.system()
            
            if system == "Windows":
                # Windows Explorer
                os.startfile(folder_path)
            elif system == "Darwin":
                # macOS Finder
                subprocess.run(["open", folder_path], check=True)
            elif system == "Linux":
                # Linux file manager (try common ones)
                subprocess.run(["xdg-open", folder_path], check=True)
            else:
                QMessageBox.information(
                    self,
                    "Unsupported OS",
                    f"Opening folders is not supported on {system}.\n\nFolder path:\n{folder_path}"
                )
        except Exception as e:
            Logger.log("e", f"Failed to open destination folder: {e}")
            QMessageBox.warning(
                self,
                "Error Opening Folder",
                f"Could not open folder:\n{folder_path}\n\nError: {str(e)}"
            )
    
    def _onStartClicked(self):
        """Handle start button click."""
        # Update model info first
        self._updateModelInfo()
        
        dest_folder = self._dest_folder_edit.text().strip()
        
        # Collect transitions first (needed for validation)
        transitions = self._collectTransitions()
        
        if not transitions:
            self._logMessage("Error: No sections defined. Add at least one section.", is_error=True)
            return
        
        # Validate transition heights
        if not self._validateTransitionHeights(transitions):
            return
        
        # Validate all inputs including transitions
        errors = self._controller.validateStartProcessing(dest_folder, transitions)
        
        if errors:
            for error in errors:
                self._logMessage(f"Error: {error}", is_error=True)
            return
        
        # Start processing
        self._setProcessingState(True)
        self._logMessage("Starting gcode fusion process...")
        self._logMessage("Using model currently on build plate...")
        
        # If transitions haven't been calculated OR calculations are invalid, auto-calculate them now
        if not self._calculated_transitions or self._calculation_invalid:
            if self._calculation_invalid:
                self._logMessage("Configuration changed - recalculating transition adjustments...")
            else:
                self._logMessage("Auto-calculating transition adjustments...")
            self._onCalculateTransitionsClicked()
        
        slice_timeout = self._slice_timeout_spin.value()
        self.startProcessing.emit(dest_folder, transitions, slice_timeout, self._calculated_transitions)
    
    def _collectTransitions(self):
        """Collect all transition definitions from the UI."""
        transitions = []
        current_height = 0.0
        
        for row in self._transition_rows:
            if not row['is_transition']:
                # This is a section
                profile_combo = row['profile_combo']
                profile_data = profile_combo.currentData()
                
                if profile_data:
                    # Get nozzle height from section (expert setting)
                    nozzle_height = 0.0
                    if 'nozzle_height_spin' in row and row['nozzle_height_spin']:
                        nozzle_height = row['nozzle_height_spin'].value()
                    
                    transitions.append({
                        'section_number': row['section_number'],
                        'start_height': current_height,
                        'end_height': None,  # Will be set by next transition or None for last
                        'profile_id': profile_data.get('container_id'),
                        'intent_category': profile_data.get('intent_category'),
                        'intent_container_id': profile_data.get('intent_container_id'),
                        'nozzle_height': nozzle_height
                    })
            else:
                # This is a transition - update previous section's end height
                if transitions:
                    height = row['height_spin'].value()
                    transitions[-1]['end_height'] = height
                    current_height = height
        
        return transitions
    
    def _validateTransitionHeights(self, transitions):
        """Validate that transition heights are in ascending order."""
        for i in range(len(transitions) - 1):
            if transitions[i]['end_height'] is not None:
                if transitions[i]['end_height'] <= transitions[i]['start_height']:
                    self._logMessage(f"Error: Transition height must be greater than 0", is_error=True)
                    return False
                
                if i + 1 < len(transitions) and transitions[i+1]['start_height'] < transitions[i]['end_height']:
                    self._logMessage(f"Error: Transition heights must be in ascending order", is_error=True)
                    return False
        
        return True
    
    def _onStopClicked(self):
        """Handle stop button click."""
        self._logMessage("Stopping gcode splicing process...")
        self.stopProcessing.emit()
    
    def _setProcessingState(self, is_processing):
        """Update UI state based on processing status."""
        self._is_processing = is_processing
        
        # Update button states
        # Use _updateStartButtonState to check both processing state and model presence
        self._updateStartButtonState()
        self._stop_btn.setEnabled(is_processing)
        
        # Update input states
        self._dest_folder_edit.setEnabled(not is_processing)
        self._dest_browse_btn.setEnabled(not is_processing)
        self._slice_timeout_spin.setEnabled(not is_processing)
        self._add_transition_btn.setEnabled(not is_processing)
        self._remove_transition_btn.setEnabled(not is_processing and len([r for r in self._transition_rows if r['is_transition']]) > 0)
        self._update_profiles_btn.setEnabled(not is_processing)
        
        # Disable all profile combos and transition controls
        for row in self._transition_rows:
            if row['profile_combo']:
                row['profile_combo'].setEnabled(not is_processing)
            if row['height_spin']:
                row['height_spin'].setEnabled(not is_processing)
            if row.get('nozzle_height_spin'):
                row['nozzle_height_spin'].setEnabled(not is_processing)
        
        # Update progress bar
        self._progress_bar.setVisible(is_processing)
        if not is_processing:
            self._progress_bar.setValue(0)
    
    def _logMessage(self, message, is_error=False):
        """Add a message to the log."""
        if is_error:
            formatted_message = f'<span style="color: {PluginConstants.ERROR_TEXT_COLOR_LIGHT_RED};">ERROR: {message}</span>'
            Logger.log("e", message)
        else:
            formatted_message = f'<span style="color: {PluginConstants.TEXT_COLOR_LIGHT_GRAY};">{message}</span>'
            
        self._log_text.append(formatted_message)
        
        # Auto-scroll to bottom
        cursor = self._log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._log_text.setTextCursor(cursor)
    
    def _displayExceptionError(self, exception):
        """Display a user-friendly error message for an exception.
        
        Args:
            exception: The exception to display (can be HellaFusionException or regular Exception)
        """
        
        if isinstance(exception, HellaFusionException):
            # Use the user-friendly message from custom exceptions
            user_message = exception.get_ui_message()
            self._logMessage(user_message, is_error=True)
            
            # Show a popup for critical errors
            if isinstance(exception, (ProfileSwitchError, BackendError, SlicingTimeoutError)):
                self._showErrorDialog("Processing Error", user_message)
        else:
            # Generic exception handling
            error_msg = f"Unexpected error: {str(exception)}"
            self._logMessage(error_msg, is_error=True)
    
    def _showErrorDialog(self, title: str, message: str):
        """Show an error dialog to the user."""

        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.setStyleSheet(PluginConstants.MESSAGE_BOX_STYLE)
        msg_box.exec()
    
    def _onTabChanged(self, index):
        """Handle tab change event - hide Clear Logs button on Transitions & Sections tab."""
        # Guard: button might not exist yet during initialization
        if not hasattr(self, '_clear_log_btn'):
            return
            
        # Tab 0 = Configuration & Control (show Clear Logs)
        # Tab 1 = Transitions & Sections (hide Clear Logs)
        if index == 1:  # Transitions & Sections tab
            self._clear_log_btn.hide()
        else:  # Configuration & Control tab
            self._clear_log_btn.show()
    
    def _clearLog(self):
        """Clear the log text area."""
        self._log_text.clear()
    
    def _loadSettings(self):
        """Load saved settings."""
        settings = self._controller.loadSettings()
        
        # Block signals to prevent triggering _saveSettings during load
        self._dest_folder_edit.blockSignals(True)
        self._slice_timeout_spin.blockSignals(True)
        
        try:
            if 'dest_folder' in settings:
                self._dest_folder_edit.setText(settings['dest_folder'])
            if 'slice_timeout' in settings:
                self._slice_timeout_spin.setValue(int(settings['slice_timeout']))
        finally:
            # Re-enable signals
            self._dest_folder_edit.blockSignals(False)
            self._slice_timeout_spin.blockSignals(False)
        
        # Update model info on load
        self._updateModelInfo()
        
        # TODO: Load transitions from settings if needed
    
    def _saveSettings(self):
        """Save current settings."""
        # Don't save during initialization
        if hasattr(self, '_is_loading') and self._is_loading:
            return
            
        settings = {
            'dest_folder': self._dest_folder_edit.text(),
            'slice_timeout': self._slice_timeout_spin.value()
        }
        
        self._controller.saveSettings(settings)
    
    def _connectSceneSignals(self):
        """Connect to scene change signals to update model info."""
        try:
            
            application = CuraApplication.getInstance()
            scene = application.getController().getScene()
            
            # Connect to scene change signal
            scene.sceneChanged.connect(self._onSceneChanged)
        except Exception as e:
            Logger.log("w", f"Could not connect to scene signals: {e}")
    
    def _onSceneChanged(self, source):
        """Handle scene changes (models added/removed/changed)."""
        # Update model info when scene changes
        self._updateModelInfo()
    
    # Signal handlers
    def _onQualityProfilesLoaded(self, quality_profiles):
        """Handle quality profiles loaded from controller."""
        self._quality_profiles = quality_profiles
        
        # Refresh all profile combos while preserving selections
        for row in self._transition_rows:
            if row['profile_combo']:
                # Store current selection
                current_data = row['profile_combo'].currentData()
                current_profile_id = None
                current_intent = None
                current_quality_name = None
                
                if current_data and isinstance(current_data, dict):
                    current_profile_id = current_data.get('container_id')
                    current_intent = current_data.get('intent_category')
                    current_quality_name = current_data.get('quality_name')
                
                # Repopulate without auto-selecting
                self._populateProfileCombo(row['profile_combo'], auto_select=False)
                
                # Restore selection if we had one
                selection_restored = False
                if current_profile_id and current_intent:
                    for i in range(row['profile_combo'].count()):
                        item_data = row['profile_combo'].itemData(i)
                        if item_data and isinstance(item_data, dict):
                            if (item_data.get('container_id') == current_profile_id and 
                                item_data.get('intent_category') == current_intent):
                                row['profile_combo'].setCurrentIndex(i)
                                selection_restored = True
                                break
                
                # Fallback to name match
                if not selection_restored and current_quality_name and current_intent:
                    for i in range(row['profile_combo'].count()):
                        item_data = row['profile_combo'].itemData(i)
                        if item_data and isinstance(item_data, dict):
                            if (item_data.get('quality_name') == current_quality_name and 
                                item_data.get('intent_category') == current_intent):
                                row['profile_combo'].setCurrentIndex(i)
                                selection_restored = True
                                break
                
                # Last resort: select first valid item
                if not selection_restored:
                    for i in range(row['profile_combo'].count()):
                        model = row['profile_combo'].model()
                        item = model.item(i)
                        if item and item.isEnabled():
                            row['profile_combo'].setCurrentIndex(i)
                            break
    
    def onProgressUpdate(self, progress):
        """Handle progress update from processing job."""
        self._progress_bar.setValue(int(progress))
    
    def onStatusUpdate(self, status):
        """Handle status update from processing job."""
        self._status_label.setText(status)
    
    def onProcessingComplete(self, results):
        """Handle processing completion."""
        self._setProcessingState(False)
        
        success = results.get('success', False)
        if success:
            self._status_label.setText("Complete")
            self._logMessage("Processing complete!")
        else:
            self._status_label.setText("Failed")
            error = results.get('error_message', 'Unknown error')
            self._logMessage(f"Processing failed: {error}", is_error=True)
    
    def onProcessingError(self, error_message, exception=None):
        """Handle processing error."""
        self._setProcessingState(False)
        self._status_label.setText("Error")
        
        if exception:
            # Display user-friendly exception message
            self._displayExceptionError(exception)
        else:
            # Fallback to generic error message
            self._logMessage(error_message, is_error=True)
    
    def _invalidateCalculations(self):
        """Invalidate current transition calculations due to changes."""
        if self._calculated_transitions:
            Logger.log("i", "Transition calculations invalidated due to configuration changes")
            self._calculated_transitions = None
            self._calculation_invalid = True
            
            # Update UI to show calculations are needed
            self._logMessage("Configuration changed - transition calculations invalidated. "
                           "Please recalculate transitions before processing.", is_error=False)
    
    def _onTransitionHeightChanged(self):
        """Handle changes to transition heights."""
        self._invalidateCalculations()
        self._saveSettings()
    
    def _onProfileSelectionChanged(self):
        """Handle changes to profile selections.""" 
        self._invalidateCalculations()
        self._saveSettings()
    
    def _onExpertSettingsToggled(self, state):
        """Handle expert settings checkbox toggle - show/hide nozzle height fields."""
        show_expert = (state == Qt.CheckState.Checked.value)
        
        # Show/hide nozzle height fields for all section rows (not transitions)
        for row in self._transition_rows:
            if not row['is_transition']:  # Sections only
                if 'nozzle_height_label' in row and row['nozzle_height_label']:
                    row['nozzle_height_label'].setVisible(show_expert)
                if 'nozzle_height_spin' in row and row['nozzle_height_spin']:
                    row['nozzle_height_spin'].setVisible(show_expert)
        
        # Save the expert settings state
        self._saveSettings()
    
    def _connectInvalidationHandlers(self):
        """Connect existing UI elements to invalidation handlers."""
        # Connect existing transition height spinboxes
        for row in self._transition_rows:
            if row['is_transition'] and row['height_spin']:
                # Disconnect any existing connections to avoid duplicates
                try:
                    row['height_spin'].valueChanged.disconnect()
                except:
                    pass  # No existing connections
                row['height_spin'].valueChanged.connect(self._onTransitionHeightChanged)
            
            if not row['is_transition'] and row['profile_combo']:
                # Disconnect any existing connections to avoid duplicates
                try:
                    row['profile_combo'].currentIndexChanged.disconnect()
                except:
                    pass  # No existing connections
                row['profile_combo'].currentIndexChanged.connect(self._onProfileSelectionChanged)

    def _show_help_dialog(self):
        """Show the help dialog."""
        dialog = HelpDialog(self.help_content, parent=self)
        dialog.exec()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        if self._is_processing:
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Icon.Question)
            msg_box.setWindowTitle('Splicing in Progress')
            msg_box.setText('Gcode splicing is in progress. Are you sure you want to close?')
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            msg_box.setStyleSheet(PluginConstants.MESSAGE_BOX_STYLE)
            
            reply = msg_box.exec()
            
            if reply == QMessageBox.StandardButton.Yes:
                self.stopProcessing.emit()
            else:
                event.ignore()
                return
        
        super().closeEvent(event)
