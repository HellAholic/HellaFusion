# HellaFusion Plugin for Cura
# Pause Settings Dialog for configuring pause-at-transition gcode
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit, 
                              QPushButton, QLabel, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from .PluginConstants import PluginConstants


class PauseSettingsDialog(QDialog):
    """Dialog for editing pause gcode that runs at transitions."""
    
    # Signals
    pauseGcodeChanged = pyqtSignal(str)  # Emitted when Save is clicked
    pauseGcodeAppliedToAll = pyqtSignal(str)  # Emitted when Apply to All is clicked
    
    def __init__(self, current_gcode, transition_number, parent=None, default_gcode=None):
        """Initialize the pause settings dialog.
        
        Args:
            current_gcode: Current pause gcode for this transition
            transition_number: The transition number (for display)
            parent: Parent widget
            default_gcode: Custom default pause gcode (if None, uses built-in default)
        """
        super().__init__(parent)
        
        self._default_gcode = default_gcode if default_gcode else PluginConstants.DEFAULT_PAUSE_GCODE
        self._current_gcode = current_gcode if current_gcode else self._default_gcode
        self._transition_number = transition_number
        
        self.setWindowTitle(f"Pause Settings - Transition {transition_number}")
        self.setModal(True)
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setStyleSheet(PluginConstants.DIALOG_BACKGROUND_STYLE)
        
        self._initUI()
        
    def _initUI(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title and instructions
        title_label = QLabel(f"Pause Gcode for Transition {self._transition_number}")
        title_label.setStyleSheet(PluginConstants.LABEL_STYLE_TITLE)
        layout.addWidget(title_label)
        
        instruction_label = QLabel(
            "Edit the gcode that will be inserted before this transition.\n"
            "This code runs when the printer pauses for a nozzle change or filament swap."
        )
        instruction_label.setStyleSheet(PluginConstants.LABEL_STYLE)
        instruction_label.setWordWrap(True)
        layout.addWidget(instruction_label)
        
        # Gcode text editor
        self._gcode_edit = QTextEdit()
        self._gcode_edit.setPlainText(self._current_gcode)
        self._gcode_edit.setStyleSheet(PluginConstants.LOG_STYLE)
        self._gcode_edit.setAcceptRichText(False)
        self._gcode_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._gcode_edit.setToolTip(
            "Enter the gcode commands to execute at this transition.\n"
            "Typically includes: retract, park, pause, purge, and return movements."
        )
        layout.addWidget(self._gcode_edit)
        
        # Help text
        help_label = QLabel(
            "Tip: The return-to-position and final unretract will be handled automatically by HellaFusion."
        )
        help_label.setStyleSheet(PluginConstants.LABEL_STYLE_HELP)
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        # Restore Default button (left side)
        self._restore_btn = QPushButton("Restore Default")
        self._restore_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._restore_btn.setToolTip("Restore the default pause gcode template")
        self._restore_btn.clicked.connect(self._onRestoreDefault)
        button_layout.addWidget(self._restore_btn)
        
        button_layout.addStretch()
        
        # Apply to All button
        self._apply_all_btn = QPushButton("Apply to All")
        self._apply_all_btn.setStyleSheet(PluginConstants.PRIMARY_BUTTON_STYLE)
        self._apply_all_btn.setToolTip("Apply this gcode to all transitions")
        self._apply_all_btn.clicked.connect(self._onApplyToAll)
        button_layout.addWidget(self._apply_all_btn)
        
        # Save button
        self._save_btn = QPushButton("Save")
        self._save_btn.setStyleSheet(PluginConstants.PRIMARY_BUTTON_STYLE)
        self._save_btn.setToolTip("Save this gcode for this transition only")
        self._save_btn.clicked.connect(self._onSave)
        button_layout.addWidget(self._save_btn)
        
        # Cancel button
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setStyleSheet(PluginConstants.SECONDARY_BUTTON_STYLE)
        self._cancel_btn.setToolTip("Close without saving")
        self._cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self._cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _onRestoreDefault(self):
        """Restore the default pause gcode template."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle('Restore Default')
        msg_box.setText('Restore the default pause gcode template? Any custom changes will be lost.')
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(PluginConstants.MESSAGE_BOX_STYLE)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            self._gcode_edit.setPlainText(self._default_gcode)
    
    def _onSave(self):
        """Save the current gcode for this transition only."""
        gcode = self._gcode_edit.toPlainText()
        self.pauseGcodeChanged.emit(gcode)
        self.accept()
    
    def _onApplyToAll(self):
        """Apply this gcode to all transitions."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Question)
        msg_box.setWindowTitle('Apply to All Transitions')
        msg_box.setText('Apply this pause gcode to all transitions? This will overwrite any custom pause settings for other transitions.')
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)
        msg_box.setStyleSheet(PluginConstants.MESSAGE_BOX_STYLE)
        
        reply = msg_box.exec()
        
        if reply == QMessageBox.StandardButton.Yes:
            gcode = self._gcode_edit.toPlainText()
            self.pauseGcodeAppliedToAll.emit(gcode)
            self.accept()
