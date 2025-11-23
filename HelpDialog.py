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

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QListWidget, QListWidgetItem, QSplitter)
from PyQt6.QtCore import Qt

from .PluginConstants import PluginConstants


class HelpDialog(QDialog):
    """Help dialog with topic list and content display."""
    
    def __init__(self, help_topics, parent=None):
        super().__init__(parent)
        self.help_topics = help_topics
        self.setWindowTitle("HellaFusion - Help")
        self.setFixedSize(PluginConstants.DIALOG_MIN_WIDTH, PluginConstants.DIALOG_MIN_HEIGHT)
        self.setStyleSheet(PluginConstants.DIALOG_BACKGROUND_STYLE)

        layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Topic list on the left
        self.topic_list_widget = QListWidget()
        self.topic_list_widget.setMaximumWidth(220)
        self.topic_list_widget.setStyleSheet(PluginConstants.HELP_PAGE_STYLE)

        # Content display on the right
        self.content_display_area = QTextEdit()
        self.content_display_area.setReadOnly(True)
        self.content_display_area.setStyleSheet(PluginConstants.HELP_PAGE_STYLE)

        splitter.addWidget(self.topic_list_widget)
        splitter.addWidget(self.content_display_area)
        splitter.setSizes([135, 465])

        layout.addWidget(splitter)

        # Close button (right-aligned)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton("Close")
        close_button.setStyleSheet(PluginConstants.WARNING_BUTTON_STYLE)
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)

        self._populate_topics()
        self.topic_list_widget.currentItemChanged.connect(self._on_topic_selected)

        # Select first topic (overview) by default
        if self.topic_list_widget.count() > 0:
            self.topic_list_widget.setCurrentRow(0)

    def _populate_topics(self):
        """Populate the topic list."""
        # Order topics in a logical sequence
        topic_order = ["overview", "transitions", "profiles", "slicing", "troubleshooting"]
        
        for topic_key in topic_order:
            if topic_key in self.help_topics:
                item = QListWidgetItem(self.help_topics[topic_key]["title"])
                item.setData(Qt.ItemDataRole.UserRole, topic_key)
                self.topic_list_widget.addItem(item)

    def _on_topic_selected(self, current_item, previous_item):
        """Handle topic selection."""
        if current_item:
            topic_key = current_item.data(Qt.ItemDataRole.UserRole)
            if topic_key in self.help_topics:
                self.content_display_area.setHtml(self.help_topics[topic_key]["content"])
