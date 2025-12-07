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

class PluginConstants:
    """Constants for UI styling and configuration."""
    
    # Dialog dimensions
    DIALOG_MIN_WIDTH = 700
    DIALOG_MIN_HEIGHT = 650
    DIALOG_MAX_WIDTH = 700
    
    # Processing configuration
    DEFAULT_SLICE_TIMEOUT = 300  # seconds
    BACKEND_STATE_CHECK_INTERVAL = 0.1  # seconds
    BACKEND_SETTLING_TIME = 0.2  # seconds after profile switch
    MAX_BACKEND_STATE_RETRIES = 10
    SLICE_START_TIMEOUT = 15.0  # seconds to wait for slice to start
    SLICE_START_MAX_TIMEOUT = 30.0  # absolute maximum time to wait for slice start
    STATUS_UPDATE_INTERVAL = 3.0  # seconds between progress status updates
    PROFILE_SWITCH_RETRY_DELAY = 1.0  # seconds to wait before retrying profile switch
    
    # Progress tracking
    COMBINING_PROGRESS_START = 90  # Start combining phase at 90% progress
    FINAL_PROGRESS = 100
    
    # File management
    TEMP_FILE_PREFIX = "hellafusion_temp_"
    OUTPUT_FILE_SUFFIX = "_hellafused"
    DEFAULT_LAYER_HEIGHT = 0.2  # mm - fallback when layer height can't be determined
    REMOVE_TEMP_FILES = True  # Whether to remove temporary files after processing
    
    # Intelligent priming constants
    PRIME_LONG_TRAVEL_THRESHOLD = 50.0  # mm - XY travel distance considered "long"
    PRIME_LONG_TIME_THRESHOLD = 5.0  # seconds - travel time considered "long"
    PRIME_LARGE_Z_CHANGE_THRESHOLD = 10.0  # mm - Z change considered "significant"
    PRIME_LAYER_HEIGHT_RATIO_HIGH = 1.5  # ratio above which layer height change is significant
    PRIME_LAYER_HEIGHT_RATIO_LOW = 0.7  # ratio below which layer height change is significant
    PRIME_MAX_MULTIPLIER = 2.0  # maximum multiplier for prime amount
    PRIME_MIN_AMOUNT = 0.1  # mm - minimum prime amount
    PRIME_PROFILE_CHANGE_ADJUSTMENT = 0.15  # adjustment factor for profile changes
    PRIME_TRAVEL_ADJUSTMENT_FACTOR = 500  # denominator for travel distance adjustment
    PRIME_TIME_ADJUSTMENT_FACTOR = 50  # denominator for travel time adjustment
    PRIME_Z_ADJUSTMENT_FACTOR = 100  # denominator for Z change adjustment
    
    DARK_BACKGROUND_COLOR = "#2d2d2d"
    BACKGROUND_COLOR = "#2d2d2d"
    TEXT_COLOR = "#E0E0E0"
    TEXT_COLOR_LIGHT_GRAY = "#E0E0E0"
    TEXT_INPUT_BG_COLOR_DARK_GRAY = "#3c3c3c"
    TEXT_INPUT_BORDER_COLOR_GRAY = "#505050"
    ERROR_TEXT_COLOR_LIGHT_RED = "#FF6B6B"
    GROUPBOX_BORDER_COLOR = "#BBBBBB"
    
    BUTTON_PRIMARY_BG = "#0078d7"
    PROGRESS_BAR_CHUNK_BG = "#00912b"
    BUTTON_PRIMARY_HOVER_BG = "#005a9e"
    BUTTON_PRIMARY_TEXT = "#FFFFFF"
    BUTTON_PRIMARY_BORDER = "#FFFFFF"

    BUTTON_CLOSE_BG = "#FFFFFF"
    BUTTON_CLOSE_TEXT = "#e81123"
    BUTTON_CLOSE_BORDER = "#e81123"
    BUTTON_CLOSE_HOVER_BG = "#f4f4f4"

    BUTTON_SECONDARY_BORDER = "#cccccc"
    BUTTON_SECONDARY_BG = "#f9f9f9"
    BUTTON_SECONDARY_TEXT = "#333333"
    BUTTON_SECONDARY_HOVER_BG = "#e0e0e0"
    
    BUTTON_DANGER_BG = "#e81123"
    BUTTON_DANGER_HOVER_BG = "#c80f1e"
    
    BUTTON_CALCULATE_BG = "#ff9800"
    BUTTON_CALCULATE_HOVER_BG = "#c77800"
    
    DIALOG_BACKGROUND_STYLE = f"background-color: {DARK_BACKGROUND_COLOR};"
    
    GROUPBOX_STYLE = f'''
        QGroupBox {{
            border: 2px solid {GROUPBOX_BORDER_COLOR};
            border-radius: 5px;
            margin-top: 20px;
        }}
        QGroupBox::title {{
            color: {TEXT_COLOR_LIGHT_GRAY};
            font-size: 13px;
            font-weight: bold;
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 0px 5px;
            left: 10px;
        }}
    '''
    
    LABEL_STYLE = f"color: {TEXT_COLOR_LIGHT_GRAY}; font-size: 13px"
    STATUS_LABEL_STYLE = f"color: {TEXT_COLOR_LIGHT_GRAY}; font-size: 13px"
    
    LINE_EDIT_STYLE = f"background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY}; color: {TEXT_COLOR_LIGHT_GRAY}; border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY}; border-radius: 3px; padding: 2px;"
    
    SPIN_BOX_STYLE = f"background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY}; color: {TEXT_COLOR_LIGHT_GRAY}; border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY}; border-radius: 3px; padding: 2px;"
    
    COMBOBOX_STYLE = f'''
        QComboBox {{
            background-color: #2b2b2b;
            color: #ffffff;
            border: 1px solid #555555;
            padding: 4px 6px;
            margin: 0px;
            min-height: 24px;
            max-height: 32px;
            border-radius: 2px;
        }}
        QComboBox:hover {{
            border: 1px solid #0078d4;
        }}
        QComboBox:focus {{
            border: 1px solid #0078d4;
            outline: none;
        }}
        QComboBox::drop-down {{
            border: none;
            background-color: #3c3c3c;
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border-left: 1px solid #555555;
        }}
        QComboBox::down-arrow {{
            border: 1px solid #666666;
            border-radius: 2px;
            background-color: #4d4d4d;
            width: 10px;
            height: 10px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #2b2b2b;
            color: #ffffff;
            selection-background-color: #0078d4;
            border: 1px solid #555555;
            margin: 0px;
            padding: 0px;
            outline: none;
        }}
        QComboBox QAbstractItemView::item {{
            padding: 6px;
            margin: 0px;
            border: none;
            min-height: 20px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: #0078d4;
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: #0078d4;
        }}
        QComboBox QAbstractItemView::item:disabled {{
            background-color: #1e1e1e;
            color: #888888;
            font-weight: bold;
            text-align: center;
        }}
    '''
    
    PRIMARY_BUTTON_STYLE = f'''
        QPushButton {{
            padding: 5px 15px; margin-left: 5px; margin-right: 5px;
            background-color: {BUTTON_PRIMARY_BG}; border: 1px solid {BUTTON_PRIMARY_BORDER};
            color: {BUTTON_PRIMARY_TEXT}; border-radius: 3px; font-size: 14px
        }} 
        QPushButton:hover {{ 
            background-color: {BUTTON_PRIMARY_HOVER_BG}; 
        }}
        QPushButton:disabled {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            color: {TEXT_INPUT_BORDER_COLOR_GRAY};
        }}
    '''
    
    SECONDARY_BUTTON_STYLE = f'''
        QPushButton {{
            padding: 5px 10px; margin-left: 5px; margin-right: 5px;
            background-color: {BUTTON_PRIMARY_BG}; border: 1px solid {BUTTON_PRIMARY_BORDER};
            color: {BUTTON_PRIMARY_TEXT}; border-radius: 3px; min-width: 80px;
        }} 
        QPushButton:hover {{ 
            background-color: {BUTTON_PRIMARY_HOVER_BG}; 
        }}
        QPushButton:disabled {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            color: {TEXT_INPUT_BORDER_COLOR_GRAY};
        }}
    '''
    
    DANGER_BUTTON_STYLE = f'''
        QPushButton {{
            padding: 5px 15px; margin-left: 5px; margin-right: 5px;
            background-color: {BUTTON_DANGER_BG}; border: 1px solid {BUTTON_CLOSE_BG};
            color: {BUTTON_PRIMARY_TEXT}; border-radius: 3px; min-width: 80px; font-size: 14px
        }} 
        QPushButton:hover {{ 
            background-color: {BUTTON_CLOSE_HOVER_BG};
            border: 1px solid {BUTTON_CLOSE_BORDER};
            color: {BUTTON_CLOSE_TEXT};
        }}
        QPushButton:disabled {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            border: 1px solid {BUTTON_CLOSE_BORDER};
            color: {TEXT_INPUT_BORDER_COLOR_GRAY};
        }}
    '''
    
    CALCULATE_BUTTON_STYLE = f'''
        QPushButton {{
            padding: 5px 15px; margin-left: 5px; margin-right: 5px;
            background-color: {BUTTON_CALCULATE_BG}; border: 1px solid {BUTTON_PRIMARY_BORDER};
            color: {BUTTON_PRIMARY_TEXT}; border-radius: 3px; min-width: 80px; font-size: 14px; font-weight: bold;
        }} 
        QPushButton:hover {{ 
            background-color: {BUTTON_CALCULATE_HOVER_BG};
        }}
        QPushButton:disabled {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            color: {TEXT_INPUT_BORDER_COLOR_GRAY};
        }}
    '''
    
    WARNING_BUTTON_STYLE = f'''
        QPushButton {{
            padding: 5px 10px; margin-left: 5px; margin-right: 5px;
            background-color: {BUTTON_CLOSE_BG}; border: 1px solid {BUTTON_CLOSE_BORDER};
            color: {BUTTON_CLOSE_TEXT}; border-radius: 3px; min-width: 80px;
        }} 
        QPushButton:hover {{ 
            background-color: {BUTTON_CLOSE_HOVER_BG}; 
        }}
        QPushButton:disabled {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            color: {TEXT_INPUT_BORDER_COLOR_GRAY};
        }}
    '''
    
    CHECKBOX_STYLE = f'''
        QCheckBox {{
            color: {TEXT_COLOR_LIGHT_GRAY};
            font-size: 13px;
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
        }}
        QCheckBox::indicator:unchecked {{
            border: 2px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            border-radius: 3px;
        }}
        QCheckBox::indicator:unchecked:hover {{
            border: 2px solid {BUTTON_PRIMARY_BG};
        }}
        QCheckBox::indicator:checked {{
            border: 2px solid {BUTTON_PRIMARY_BG};
            background-color: {BUTTON_PRIMARY_BG};
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: {BUTTON_PRIMARY_HOVER_BG};
            border: 2px solid {BUTTON_PRIMARY_HOVER_BG};
        }}
    '''
    
    TABLE_WIDGET_STYLE = f'''
        QTableWidget {{
            background-color: #2b2b2b;
            color: #ffffff;
            gridline-color: #555555;
            selection-background-color: #3d5aa3;
            alternate-background-color: #333333;
            border: 1px solid #555555;
        }}
        QTableWidget::item {{
            padding: 3px 5px;
            border: none;
            text-align: left;
        }}
        QTableWidget::item:selected {{
            background-color: #3d5aa3;
            color: #ffffff;
        }}
        QHeaderView::section {{
            background-color: #404040;
            color: #ffffff;
            padding: 8px 5px;
            border: 1px solid #555555;
            font-weight: bold;
            text-align: left;
        }}
    '''
    
    PROGRESS_BAR_STYLE = f'''
        QProgressBar {{
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            border-radius: 3px;
            text-align: center;
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            color: {TEXT_COLOR_LIGHT_GRAY};
        }}
        QProgressBar::chunk {{
            background-color: {PROGRESS_BAR_CHUNK_BG};
            border-radius: 2px;
        }}
    '''
    
    LOG_STYLE = f'''
        QTextEdit {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            color: {TEXT_COLOR_LIGHT_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            padding: 5px;
            border-radius: 3px;
        }}
        QTextEdit QScrollBar:vertical {{
            background-color: #2b2b2b;
            width: 12px;
            margin: 0px;
        }}
        QTextEdit QScrollBar::handle:vertical {{
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }}
        QTextEdit QScrollBar::handle:vertical:hover {{
            background-color: #666666;
        }}
        QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    '''
    
    TAB_WIDGET_STYLE = '''
        QTabWidget::pane {
            border: 2px solid #555555;
            background-color: #2b2b2b;
            border-radius: 4px;
            margin-top: -1px;
        }
        QTabBar::tab {
            background-color: #1a1a1a;
            color: #888888;
            padding: 10px 20px;
            margin-right: 4px;
            margin-top: 2px;
            border: 2px solid #3d3d3d;
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            min-width: 120px;
            font-size: 13px;
            font-weight: normal;
        }
        QTabBar::tab:selected {
            background-color: #2b2b2b;
            color: #ffffff;
            border: 2px solid #555555;
            border-bottom: 2px solid #2b2b2b;
            margin-top: 0px;
            padding-top: 12px;
            font-weight: bold;
        }
        QTabBar::tab:hover:!selected {
            background-color: #0078d7;
            color: #ffffff;
            border: 2px solid #0078d7;
            border-bottom: none;
        }
        QTabBar::tab:disabled {
            background-color: #2a2a2a;
            color: #555555;
            border: 2px solid #333333;
            border-bottom: none;
        }
    '''
    
    # Scroll Area Style
    SCROLL_AREA_STYLE = '''
        QScrollArea {
            background-color: #2b2b2b;
            border: 1px solid #3d3d3d;
            border-radius: 4px;
        }
        QScrollBar:vertical {
            background-color: #2b2b2b;
            width: 12px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #666666;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    '''
    
    # Transparent Widget Style
    TRANSPARENT_WIDGET_STYLE = "background-color: transparent;"
    
    # Message Box Style
    MESSAGE_BOX_STYLE = f'''
        QMessageBox {{
            background-color: {DARK_BACKGROUND_COLOR};
            color: {TEXT_COLOR_LIGHT_GRAY};
        }}
        QMessageBox QLabel {{
            color: {TEXT_COLOR_LIGHT_GRAY};
            font-size: 13px;
        }}
        QMessageBox QPushButton {{
            background-color: {BUTTON_PRIMARY_BG};
            color: {BUTTON_PRIMARY_TEXT};
            border: 1px solid {BUTTON_PRIMARY_BORDER};
            border-radius: 3px;
            padding: 6px 16px;
            min-width: 60px;
            font-weight: bold;
        }}
        QMessageBox QPushButton:hover {{
            background-color: {BUTTON_PRIMARY_HOVER_BG};
        }}
        QMessageBox QPushButton:pressed {{
            background-color: #004578;
        }}
    '''
    
    # Help Button Style
    HELP_BUTTON_STYLE = f'''
        QPushButton {{
            background-color: {BUTTON_PRIMARY_BG};
            color: {BUTTON_PRIMARY_TEXT};
            border: 1px solid {BUTTON_PRIMARY_BORDER};
            border-radius: 10px;
            min-width: 20px;
            max-width: 20px;
            min-height: 20px;
            max-height: 20px;
            font-weight: bold;
            font-size: 12px;
            margin-top: 0px;
            margin-right: 5px;
            margin-bottom: 10px;
        }}
        QPushButton:hover {{
            background-color: {BUTTON_PRIMARY_HOVER_BG};
        }}
    '''
    
    # Help Page Style
    HELP_PAGE_STYLE = f'''
        QListWidget {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            color: {TEXT_COLOR_LIGHT_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            padding: 5px;
            border-radius: 3px;
        }}
        QListWidget:focus {{
            outline: none;
        }}
        QListWidget::item {{
            padding: 8px;
            border-radius: 3px;
        }}
        QListWidget::item:selected {{
            background-color: {BUTTON_PRIMARY_BG};
            color: {BUTTON_PRIMARY_TEXT};
        }}
        QListWidget::item:hover:!selected {{
            background-color: #404040;
        }}
        QListWidget QScrollBar:vertical {{
            background-color: #2b2b2b;
            width: 12px;
            margin: 0px;
        }}
        QListWidget QScrollBar::handle:vertical {{
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }}
        QListWidget QScrollBar::handle:vertical:hover {{
            background-color: #666666;
        }}
        QListWidget QScrollBar::add-line:vertical, QListWidget QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QTextEdit {{
            background-color: {TEXT_INPUT_BG_COLOR_DARK_GRAY};
            color: {TEXT_COLOR_LIGHT_GRAY};
            border: 1px solid {TEXT_INPUT_BORDER_COLOR_GRAY};
            padding: 10px;
            font-size: 13px;
            border-radius: 3px;
        }}
        QTextEdit QScrollBar:vertical {{
            background-color: #2b2b2b;
            width: 12px;
            margin: 0px;
        }}
        QTextEdit QScrollBar::handle:vertical {{
            background-color: #555555;
            border-radius: 6px;
            min-height: 20px;
        }}
        QTextEdit QScrollBar::handle:vertical:hover {{
            background-color: #666666;
        }}
        QTextEdit QScrollBar::add-line:vertical, QTextEdit QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
    '''
    
    # Label Variants
    LABEL_STYLE_GRAY = f"{LABEL_STYLE}; color: #aaaaaa;"
    LABEL_STYLE_SUCCESS = f"{LABEL_STYLE}; color: #4CAF50;"
    LABEL_STYLE_WARNING = f"{LABEL_STYLE}; color: #FFA726;"
    LABEL_STYLE_ERROR = f"{LABEL_STYLE}; color: #F44336;"
    LABEL_STYLE_SECTION = f"{LABEL_STYLE}; font-weight: bold; min-width: 80px;"
    LABEL_STYLE_TRANSITION = f"{LABEL_STYLE}; color: #00912b; font-weight: bold; min-width: 120px;"

    HELP_CONTENT = {
        "overview": {
            "title": "Overview",
            "content": """
                <h2>🔥 HellaFusion - Advanced Multi-Quality Printing</h2>
                <p><b>Revolutionary 3D printing technology</b> that enables <b>dynamic quality switching</b> within a single print job. Print different sections of your model with completely different quality profiles!</p>
                
                <h3>🚀 Perfect For:</h3>
                <ul>
                    <li><b>Speed + Quality Fusion:</b> Draft mode for hidden sections, fine detail where it matters</li>
                    <li><b>Structural Optimization:</b> Heavy infill for bases, lightweight for tops</li>
                    <li><b>Material Efficiency:</b> Balance strength, speed, and material usage intelligently</li>
                    <li><b>Advanced Prototyping:</b> Test multiple quality settings in a single print</li>
                    <li><b>Complex Geometries:</b> Adapt quality to each section's requirements</li>
                </ul>
                
                <h3>⚡ Advanced Fusion Technology:</h3>
                <p>HellaFusion uses intelligent algorithms to slice your model multiple times with different quality profiles, then <b>seamlessly fuses</b> the gcode sections with:</p>
                <ul>
                    <li><b>Smart Layer Alignment:</b> Automatic initial layer height adjustments</li>
                    <li><b>Perfect Transitions:</b> Seamless quality switches at optimal points</li>
                    <li><b>Intelligent Analysis:</b> Real-time calculation of optimal fusion parameters</li>
                </ul>
                
                <p><b>📍 Important:</b> The same model on your build plate is used for all sections - only the slicing settings change to create the fusion effect.</p>
            """
        },
        "transitions": {
            "title": "Setting Up Transitions",
            "content": """
                <h2>🎯 Mastering Fusion Transitions</h2>
                <p><b>Transitions are fusion points</b> where HellaFusion switches from one quality profile to another. Each section between transitions uses a completely different quality profile for optimal results.</p>
                
                <h3>🔄 How Fusion Transitions Work:</h3>
                <ul>
                    <li><b>Section 1:</b> Z=0mm → First transition (uses Profile A)</li>
                    <li><b>Fusion Point:</b> Seamless quality switch at Z=X mm</li>
                    <li><b>Section 2:</b> Z=X mm → Next transition (uses Profile B)</li>
                    <li><b>Unlimited Sections:</b> Add as many fusion points as needed!</li>
                </ul>
                
                <h3>🧠 Pro Fusion Strategies:</h3>
                <ul>
                    <li><b>🏗️ Structural Transitions:</b> Plan fusion points at model features - between flat sections, after support structures</li>
                    <li><b>🎨 Visual Optimization:</b> Avoid mid-feature transitions - never fuse in the middle of thin walls or critical details</li>
                    <li><b>⚡ Smart Alignment:</b> HellaFusion automatically aligns to optimal layer boundaries for seamless fusion</li>
                    <li><b>📏 Height Logic:</b> Transitions must be in ascending Z-height order for proper fusion sequencing</li>
                </ul>
                
                <h3>🛠️ Fusion Control Panel:</h3>
                <ul>
                    <li><b>➕ Add Transition:</b> Creates new fusion point and next section</li>
                    <li><b>➖ Remove Last Transition:</b> Removes most recent fusion point</li>
                    <li><b>✅ Smart Validation:</b> Real-time checks ensure proper fusion order and model compatibility</li>
                    <li><b>🧮 Calculate Transitions:</b> Advanced analysis for optimal fusion parameters</li>
                </ul>
            """
        },
        "profiles": {
            "title": "Quality Profiles",
            "content": """
                <h2>🎨 Quality Profile Fusion</h2>
                <p>Each section can use a <b>completely different quality profile</b> from your Cura configuration. This is where <b>HellaFusion's true power</b> is unleashed!</p>
                
                <h3>🏷️ Available Profile Categories:</h3>
                <p>HellaFusion automatically detects all profiles compatible with your current printer and material setup:</p>
                <ul>
                    <li><b>🔧 Default Profiles:</b> Standard quality options (Draft, Normal, Fine, Ultra Fine)</li>
                    <li><b>⚙️ Engineering Profiles:</b> Optimized for strength, durability, and mechanical properties</li>
                    <li><b>✨ Visual Profiles:</b> Perfect surface quality and aesthetic finish</li>
                    <li><b>🎯 Custom Profiles:</b> Your personalized profiles (marked with ⭐)</li>
                </ul>
                
                <h3>🔄 Smart Profile Management:</h3>
                <p><b>Reload Profiles Button</b> - Use when you:</p>
                <ul>
                    <li>🖨️ Switch printer configurations in Cura</li>
                    <li>🧵 Change materials or nozzle sizes</li>
                    <li>➕ Create or modify custom quality profiles</li>
                    <li>🔧 Update printer firmware or settings</li>
                </ul>
                <p><b>Smart Refresh:</b> Updates available profiles without losing your current section selections!</p>
                
                <h3>🧠 Pro Fusion Tips:</h3>
                <ul>
                    <li><b>⚡ Layer Height Harmony:</b> Similar layer heights between sections create smoother transitions</li>
                    <li><b>🏃 Speed Consistency:</b> Moderate speed changes prevent extrusion artifacts at fusion points</li>
                    <li><b>🧪 Test First:</b> Experiment with profile combinations on small test models</li>
                    <li><b>🎯 Strategic Selection:</b> Match profile characteristics to each section's requirements</li>
                </ul>
            """
        },
        "slicing": {
            "title": "Slicing Process",
            "content": """
                <h2>How the Slicing Process Works</h2>
                <p>The plugin uses a two-step process for optimal layer alignment between sections:</p>
                
                <h3>Step 1: Calculate Transitions (Recommended)</h3>
                <p>Click the <b>"Calculate Transitions"</b> button (orange) before slicing to:</p>
                <ul>
                    <li><b>Analyze layer alignment:</b> Checks where layers will actually end for each section</li>
                    <li><b>Calculate adjustments:</b> Determines optimal initial layer height for each section to align with the previous section's layers</li>
                    <li><b>Minimize gaps:</b> Chooses whether to align above or below to minimize adjustments</li>
                    <li><b>Display preview:</b> Shows Z-ranges, layer heights, and proposed adjustments</li>
                </ul>
                <p><b>Why calculate first?</b> Different profiles have different layer heights. Without adjustment, layers may not align at transitions, causing gaps or overlaps.</p>
                <p><b>Warnings:</b> The calculator will warn you if:</p>
                <ul>
                    <li><b>Adaptive Layer Height</b> is enabled (may conflict with adjustments)</li>
                    <li><b>Tree Support</b> is enabled (non-deterministic between slices, can cause floating support)</li>
                </ul>
                
                <h3>Step 2: Start Fusing</h3>
                <p>Click <b>"Start Fusing"</b> to perform the actual fusing:</p>

                <h4>2a. Model Detection</h4>
                <p>The plugin detects the model currently on your build plate.</p>
                
                <h4>2b. Profile Switching and Slicing</h4>
                <p>For each section:</p>
                <ol>
                    <li>Switches to the selected quality profile</li>
                    <li><b>Applies initial layer height adjustment</b> (if calculated and needed) to align layers</li>
                    <li>Waits for Cura to slice the model</li>
                    <li>Saves the gcode to a temporary file</li>
                    <li>Records actual layer heights achieved</li>
                </ol>
                <p><b>Note:</b> Section 1 is never adjusted (it's the build plate adhesion layer). Each subsequent section is adjusted to align with where the previous section actually ended.</p>
                
                <h4>2c. Gcode Extraction</h4>
                <p>The plugin extracts the relevant Z-height ranges from each gcode file:</p>
                <ul>
                    <li>Parses gcode to track Z position</li>
                    <li>Identifies layer boundaries based on actual layer heights</li>
                    <li>Extracts only layers within each section's range</li>
                    <li>Transitions always occur at layer boundaries (never mid-layer)</li>
                </ul>
                
                <h4>2d. Intelligent Combining</h4>
                <p>Combines the sections into one file:</p>
                <ul>
                    <li>Uses startup gcode from Section 1</li>
                    <li>Fuses sections at exact layer boundaries</li>
                    <li>Maintains E (extrusion) continuity across sections</li>
                    <li>Uses shutdown gcode from the final section</li>
                </ul>
                
                <h4>2e. Output</h4>
                <p>Final gcode is saved to your destination folder with a timestamp. Temporary files are automatically cleaned up.</p>
                
                <h3>Manual vs Auto-Calculate:</h3>
                <ul>
                    <li><b>Click Calculate first (Recommended):</b> Preview adjustments before slicing</li>
                    <li><b>Skip Calculate:</b> Plugin auto-calculates when you click Start Fusing</li>
                </ul>
                
                <h3>Timeout Setting:</h3>
                <p>The <b>Slice Timeout</b> (default 300s) prevents infinite waiting if slicing fails. Increase for complex models.</p>
            """
        },
        "troubleshooting": {
            "title": "Troubleshooting",
            "content": """
                <h2>Common Issues and Solutions</h2>
                <h3>Slicing Timeout</h3>
                <p><b>Problem:</b> "Slicing timeout" error appears</p>
                <p><b>Solutions:</b></p>
                <ul>
                    <li>Increase the Slice Timeout value in Configuration</li>
                    <li>Simplify your model (reduce polygon count)</li>
                    <li>Check if Cura is responsive (not frozen)</li>
                    <li>Try slicing manually in Cura first to verify the model and settings work</li>
                </ul>
                <h3>Transition Height Validation Errors</h3>
                <p><b>Problem:</b> "Transition heights must be in ascending order" error</p>
                <p><b>Solutions:</b></p>
                <ul>
                    <li>Check that each transition height is greater than the previous one</li>
                    <li>Remove and re-add transitions in the correct order</li>
                    <li>Ensure transition heights are less than your model height</li>
                </ul>
                <h3>Quality Profile Issues</h3>
                <p><b>Problem:</b> Expected profiles not showing in dropdowns</p>
                <p><b>Solutions:</b></p>
                <ul>
                    <li>Click "Reload Profiles from Cura" button</li>
                    <li>Verify the profile exists for your current printer and material in Cura's normal slicing view</li>
                    <li>Check that your printer definition supports the profile</li>
                </ul>
                <h3>Visual Artifacts at Transitions</h3>
                <p><b>Problem:</b> Visible lines or imperfections where sections meet</p>
                <p><b>Solutions:</b></p>
                <ul>
                    <li>Use profiles with similar layer heights to minimize Z-seam visibility</li>
                    <li>Position transitions at model features (edges, flat surfaces) where they're less noticeable</li>
                    <li>Ensure both profiles use compatible print speeds and temperatures</li>
                    <li>Consider adding a small transition buffer in your model design</li>
                </ul>
                <h3>Processing Failed During Combining</h3>
                <p><b>Problem:</b> Error occurs during the combining step</p>
                <p><b>Solutions:</b></p>
                <ul>
                    <li>Check the Processing Log for specific error messages</li>
                    <li>Verify all sections sliced successfully</li>
                    <li>Try reducing the number of transitions</li>
                    <li>Check destination folder permissions</li>
                </ul>
            """
        }
    }
