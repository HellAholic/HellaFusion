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
    HELP_DIALOG_MIN_WIDTH = 800
    HELP_DIALOG_MIN_HEIGHT = 600
    
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
    
    # Default pause at transition gcode template
    DEFAULT_PAUSE_GCODE = """;========== Pause before Transition ==========
M83                                    ; Relative extrusion (required for E movements)
G1 F2100 E-4.0                        ; Retract filament before parking
G0 F2400 X0 Y0                        ; Park at X0 Y0 (edit coordinates as needed)
M84 S6000                             ; Hold the steppers on for 6000 seconds
M300                                  ; Beep to alert user
M0                                    ; Pause command (works with most firmwares)
G1 F200 E35                           ; Purge material after nozzle change
G1 F200 E-4.0                         ; Retract after purge
G4 S2                                 ; Wait 2 seconds for user to remove purge string
; Note: Return position and final unretract will be added by HellaFusion
M82                                   ; Absolute extrusion mode
;========== Resume Printing =========="""
    
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
    LABEL_STYLE_MUTED = f"{LABEL_STYLE}; color: #aaaaaa;"  # Alias for help/hint text
    LABEL_STYLE_HELP = f"{LABEL_STYLE}; color: #aaaaaa; font-style: italic;"  # For italic help text
    LABEL_STYLE_SUCCESS = f"{LABEL_STYLE}; color: #4CAF50;"
    LABEL_STYLE_WARNING = f"{LABEL_STYLE}; color: #FFA726;"
    LABEL_STYLE_ERROR = f"{LABEL_STYLE}; color: #F44336;"
    LABEL_STYLE_SECTION = f"{LABEL_STYLE}; font-weight: bold; min-width: 80px;"
    LABEL_STYLE_TRANSITION = f"{LABEL_STYLE}; color: #00912b; font-weight: bold; min-width: 120px;"
    LABEL_STYLE_TITLE = f"{LABEL_STYLE}; font-size: 14px; font-weight: bold;"  # For dialog titles

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

                
                <h3>🚀 HellaFusion opens up 'A Whole New World' of possibilities:</h3>
                <ul>
                    <li><b>Mix and Fuse different Profile Settings:</b> Have a base print at 0.25 Layer Height and 0.4 Line Width and Spiralize the upper statue portion at 0.12 Layer Height and 0.6 Line Width.</l>
                    <li><b>Nozzle Changes mid print?:</b> With 'Pause at Height' it's a possibility (will require experimentation and maybe a Z-Offset adjustment).</li>
                    <li><b>In regards to Pause at Height:</b> The first pause should be at the same Z height as a transition.  A second pause should be '1 layer height more' than the transition height.  That would put a pause before the 1st transition and a pause before the 2nd transition.</li>
                    <li><b>Color Changes with Wholesale Setting Changes:</b> Different wall count, different top/bottom layers, Layer Height, different Infill, etc. all mixed in a single print.</li>
                    <li><b>Mix compatible materials.</b>  Again using Pause at Height - Print TPU on a PETG base and then switch back to PETG.</li>
                </ul>

                <h3>​📢​ Fabulous Rave Reviews about <b><i>HellaFusion</i></b>:</h3>
                <ul>
                    <li>​​​🙈​<b><i>"I must admit I have never seen anything like it."</i></b> - Helen Keller</li>
                    <li>💀<b><i>"I'm dead. Leave me alone."</i></b> - Leonardo DaVinci</li>
                    <li>​👵​<b><i>"Holy Crap!  That is so friggin cool!!"</i></b> "Alright, I testified.  Now buy me that drink" - Some random sot at the end of the bar.</li>
                    <li>💀<b><i>"Ive seen better.  Im pretty sure I have.  I cant remember when, but I must have."</i></b> - Greg Valiant (sitting next to the random sot.)</li>
                    <li>​🤖​<b><i>"Does not compute.  Does not compute."</i></b> - HAL 9000</li>
                    <li>​👩‍🚀​<b><i>"Everybody's dead, Dave... except for this plugin, which is very much alive."</i></b> - Holly, Red Dwarf</li>
                    <li>​👽​<b><i>"Take me to your leader.  I want to show him this HellaFusion thingy."</i></b> - Alien visitor from the planet Zog.</li>
                    <li>​🔥​<b><i>"I blame Jelle, Casper 👻, and Greg!"</i></b> - HellAholic</li>
                </ul>
                <p>
                <b>📍 Please Note:</b> The same model(s) on your build plate are used for all sections - only the slicing settings change to create the fusion effect.</p>
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
                    <li><b>⚡ Layer Height Harmony:</b> Similar layer heights between sections create smoother transitions.  If you are using Layer Heights that are even numbers (0.10, 0.16, 0.24 etc.) then use Transition Heights that are also even numbers.  Having a .20 layer height transtion to a .012 Layer Height at 12.50mm will require fudging of the numbers because 12.50 is not exactly divisible by any even number.  A Transtion Height of 12.40 would be preferable.</li>
                    <li><b>🏃 Speed Consistency:</b> Moderate speed changes prevent extrusion artifacts at fusion points</li>
                    <li><b>🧪 Test First:</b> Experiment with profile combinations on small test models</li>
                    <li><b>🎯 Strategic Selection:</b> Match profile characteristics to each section's requirements</li>
                    <p>
                    <li>See 'Getting Started' for more on Profiles and why you want 'Custom' profile for each section of the print.</li>
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
        },
        "gettingstarted": {
            "title": "Getting Started",
            "content": """
                <h2>A Sample Fusion Project</h2>
                <p>The HellaFusion process can be quick and easy, or long and involved. It depends on what the User wants out of the project. A project with one 25mm cube as a model and a single transition from .25 layer height to 0.15 layer height will process quickly. A project with a hi-res model of the 'Pieta' that takes up the entire build plate, with 5 transitions and 2 "Pause at Heights" is going to take a while.</p>
                
                <p><b>Please Note:</b> HellaFusion works "By Height" because the layer numbering is a function of Initial Layer Height and Layer Height. In addition, settings like "Adaptive Layers" can effect the numbering. On the other hand...a height is a height (unless it's on a raft).</p>

                <h3>Develop your plan and write down the individual steps</h3>
                <p>You want to have a plan for each "Section" of the project file as things can rapidly get confusing. Follow along with this Practice Fusion Project. It has two transitions (at 13mm and at 21mm) and there will be a change from 0.20 Layer Height, to 0.10 Layer Height, and back to 0.20 Layer Height.</p>
                
                <p><b>Here is 'The Plan':</b></p>
                <ul>
                    <li>'Section 1': from Z0 to Z13.0 at 0.20 Layer Height and with Wall Count = 2</li>
                    <li>'Section 2': from Z13 to Z21.0 at 0.10 Layer Height and with Wall Count = 3</li>
                    <li>'Section 3': from Z21 to the End of Print at 0.20 Layer Height and Wall Count = 2</li>
                </ul>

                <p><b>'The Plan'</b> for this project will require just two Custom Profiles. Section 1 will use 'Profile 1' to start the print. Section 2 will use Profile 2. Section 3 has the same settings as Section 1 and so Profile 1 will be used to finish the print.</p>
                
                <h3>Here is how to come up with your own 'The Plan'</h3>
                <ol>
                    <li>For this example - load a model into Cura that is about 25mm tall.</li>
                    <li>Slice the model with 'Layer Height = 0.10' and 'Initial Layer Height = 0.10'. That makes for easy math as each layer is 0.1mm and so the Preview Slider ratio will be '10 Layers = 1.00mm'.</li>
                    <li>Use the Cura Preview to determine the Z heights where you want transitions. Write those 'Transition Heights' down, and note what Settings you might want to change at each height. Don't forget 'Section 1' which is the start of the print up to the first Transition Height.</li>
                    <li>Make a copy of an existing 'Quality Profile'. Choose the one that is closest to how you want to start the print. Name it 'Profile 1'.</li>
                    <li>With Profile 1 active in Cura, change the settings within 'Profile 1' so it is <i>exactly</i> how you want the print to start, then save the changes. (Please remember that neither 'Tree Supports' nor 'One at a Time' print sequence are allowed.)</li>
                    <li>Make a copy of Profile 1. (How many copies depends on how many times you are making changes within the print. This example project is making a change, and reverting, and so it only requires 'Profile 1' and 'Profile 2'.)</li>
                    <li>Activate 'Profile 2'. Alter the Layer Height to 0.10 and the Wall Count to 2. Save the changes to Profile 2.</li>
                    <li>If a project was to have more Transitions, it might require more profiles. Each succeeding profile should start as a copy of Profile 1, and then have it's particular settings adjusted, and those settings saved.</li>
                </ol>
                
                <p>With the Profiles set according to The Plan, it's time to move on to Fusion.</p>

                <h3>Fusion setup</h3>
                <p>(Make sure you select the "Destination Folder" on the "Transition Control" tab. You should consider a dedicated folder as you may be slicing several times to get things just right.)</p>

                <ol>
                    <li>In the HellaFusion dialog select the "Transition Sections" tab.</li>
                    <li>Use the 'Add Transition' button twice (our example project has 2 transitions). (The minimum is a single transition that would allow you to change settings at a height in the print and those settings would finish the print.)</li>
                    <li>Adjust the Height of Transition 1 to 13mm.</li>
                    <li>Adjust the Height of Transition 2 to 21mm.</li>
                    <li>For each 'Section' - select the custom Profile that you want to be active for that portion of the print. In this example, Section 1 = Profile 1, Section 2 = Profile 2, Section 3 = Profile 1.</li>
                    <li>Select the "Calculate Transitions" button and HellaFusion will calculate the transition parameters required to put together the transition gcode.</li>
                    <li>Select "Start Fusing" and the project will start.</li>
                </ol>

                <h2>What's going on while I'm sitting here?</h2>
                <ul>
                    <li>The 'Section 1 Profile' will be made active (in this example it's Profile 1) and the model will be sliced and saved to a temporary file. Profile 2 will be loaded, and the model will be sliced and saved to temporary. Profile 1 will be re-loaded and Section 3 will be sliced and saved to temporary.</li>
                    <li>After the slicing and saving is done, HellaFusion will open the temporary files (in this case 3 of them) and cut out the sections to be used in the final Gcode. Then the Transition code is calculated and inserted.</li>
                    <li>When the process is complete, you will see a note in the 'log' textbox that will indicate Success or Failure of the process.</li>
                </ul>

                <h3>Post-Processing Tips</h3>
                <ul>
                    <li>Open the Gcode file in a text editor. Search for "sect" to locate the transitions where the gcode has been spliced together.</li>
                    <li>Delete all those temporary Profiles. They are unlikely to be needed exactly as they are and they just add to the confusion of Fusion.</li>
                    <li>Go to your 'Save To' folder and clean out all those 'Practice Slices'.</li>
                    <li>The most common error encountered is the user inputting the Transition Heights incorrectly.</li>
                </ul>

            """
        },
        "settingshelp": {
            "title": "Help",
            "content": """
                <h2>'Configuration & Control' tab</h2>
                <ul>
                    <li><b>'Model on Build Plate'</b> - A list of the models to be sliced. (There must be a model present or the script exits).</li>
                    <li><b>'Destination Folder'</b> - The 'Save Location' of the fused files. This setting carries over from Cura session to Cura session. (Temporary files will be stored in your 'Temp' folder and deleted at the end of the fusion process unless you disable cleanup in Settings.)</li>
                    <li><b>'Slice Timeout (seconds)'</b> - A safety provided because it is a long process and if Cura gets stuck in a loop, the Timeout should ensure that the function ends in good order (rather than just a crash).</li>
                    <li><b>The 'Browse' button</b> - Used to select your 'Save To' folder.</li>
                    <li><b>The 'Open Folder' button</b> - Use to view the files in the Save To folder. You can double-click on a file to open it in your text editor, or right-click and select "Open with...". IT IS HIGHLY RECOMMENDED that you view each transition in a fused file and ensure that it will be working as expected.</li>
                    <li><b>'Show Expert Settings' checkbox</b> - Reveals advanced controls including nozzle length fields and pause-at-transition features. See below for details.</li>
                    <li><b>'Start Fusing' button</b> - When your settings are complete - this is the button to use to actually start the process.</li>
                    <li><b>'Stop' button</b> - Aborts the fusing process.</li>
                    <li><b>'Calculate Transitions' button</b> - This involves the internal calculation of the transition parameters. Making the calculations prior to 'Start Fusing' can save a bit of time.</li>
                    <li><b>'Progress Bar'</b> - Attempts to keep the user advised on the state of the fusion process and the Cura Engine progress. Along with the notes in the Log window, it provides an estimation of when the process will complete.</li>
                    <li><b>'Processing Log' text box</b> - Notes from HellaFusion regarding where it is in the process, or if problems were encountered.</li>
                    <li><b>'Clear Logs' button</b> - Empties the Processing Log textbox.</li>
                </ul>

                <h2>'Transitions & Sections' tab</h2>
                <ul>
                    <li><b>'Add Transition' button</b> - Adds a transition point to the list. You will need to pick a 'Profile' from the drop-down list for each transition section, and adjust the 'Transition at Z' value (the height where the transition is to occur). The transitions you add do NOT carry over from Cura session to Cura session. They must be created new each time.</li>
                    <li>It is easy to get confused by the changes that Fusion will make at the transitions. That is why you are urged to create 'Custom Profiles' for each section of the transition.</li>
                    <li><b>'Remove Last Transition' button</b> - Allows editing (or starting over) of the items in the transition list.</li>
                    <li><b>'Reload Profiles from Cura'</b> - HellaFusion needs to have the latest version of any profile. Temporary changes you might make while slicing and checking will not carry over unless they have been saved to the Profile. This button allows you to load the latest saved version of all the profiles.</li>
                </ul>

                <h3>🔧 Expert Settings (Transitions & Sections tab)</h3>
                <ul>
                    <li><b>'Nozzle Length' fields</b> - Visible when 'Show Expert Settings' is enabled. If you wish to make a nozzle change at a transition, you can do so but you must know the 'Stick Out' length of each nozzle. Fusion will adjust the 'Z' offset based on the difference in the length of the nozzles when going from one nozzle to the next. That is required so the Layer Height of the transition layer will be correct. This adjustment is necessary for ABL equipped machines as well as manually leveled machines. If this is a feature you would care to use, the nozzles involved must be carefully measured and then set aside for use. Not all 4mm nozzles will be the same length and you must use the one you indicated IF there will be a nozzle change. A 'Table of Nozzle Lengths' would be a good idea.</li>
                    <li><b>'Pause here' checkbox (per transition)</b> - Visible when 'Show Expert Settings' is enabled. Check this box to insert a pause before this transition. Perfect for nozzle changes, filament swaps, or color changes. When enabled, a 'Pause Settings' button appears to customize the pause gcode.</li>
                    <li><b>'Pause Settings' button (per transition)</b> - Opens a dialog where you can edit the pause gcode that will be inserted before this transition. The default template includes: retract, park position, pause command, purge, and wait time. You can customize this for your specific printer and workflow. The 'Restore Default' button in the dialog resets to your custom default (set in Settings tab). 'Apply to All' applies the current gcode to all transitions.</li>
                    <li><b>Measuring Nozzles (only required if actually changing nozzles at transitions)</b> - A typical Mark 6 nozzle will have threads at the back end, then a hex shape that transitions to the actual tip of the nozzle. You need to measure the amount of 'stick out' only. That is the distance from the back of the Hex Shape (the surface that tightens against the heat block) to the business end where the plastic comes out. The threaded portion is not part of the 'Stick Out' and you cannot use the 'overall' length of the nozzle. Almost all nozzles will have slightly different stick out measurements. I would suggest using an old heat block, tightening each 'clean' nozzle into it, and measuring the height from the block to the nozzle tip. That is the 'stick out' number you need to record for that particular nozzle.</li>
                </ul>

                <h2>'Settings' tab</h2>
                
                <h3>File Management</h3>
                <ul>
                    <li><b>'Remove temporary files after processing' checkbox</b> - When enabled (default), temporary sliced gcode files are automatically deleted after successful fusion. Disable if you want to inspect the individual section files for debugging.</li>
                    <li><b>'Temporary files location'</b> - Path where temporary sliced files are stored during processing. Leave empty to use system temp directory. Use the 'Browse...' button to select a custom location.</li>
                    <li><b>'Temporary file prefix'</b> - Prefix used for temporary file names (default: "hellafusion_temp_"). Useful if you want to identify HellaFusion temp files easily.</li>
                    <li><b>'Output file suffix'</b> - Suffix appended to output file names before the timestamp (default: "_hellafused"). Example: model_hellafused_20231207_143022.gcode</li>
                </ul>

                <h3>UI Behavior</h3>
                <ul>
                    <li><b>'Hide Calculate Transitions button' checkbox</b> - Hides the 'Calculate Transitions' button from the Configuration tab. Auto-calculation will still occur when you click 'Start Fusing'. Useful to reduce UI clutter if you always rely on auto-calculation.</li>
                </ul>

                <h3>Default Pause Settings</h3>
                <ul>
                    <li><b>'Default Pause Gcode' text editor</b> - Configure the default pause gcode template used for new transitions with pause enabled. This gcode runs when the printer pauses for nozzle changes or filament swaps. The default includes: retract, park, pause command (M0), purge, and wait time. Customize for your printer's firmware and workflow. Changes are saved automatically.</li>
                    <li><b>'Reset to Built-in Template' button</b> - Resets the default pause gcode to the plugin's original built-in template. Use this if you've customized the template and want to start over with the default.</li>
                    <li><b>'Save' button</b> - Saves the current default pause gcode settings. Although changes auto-save, this button provides explicit confirmation that your settings have been saved.</li>
                </ul>

                <h3>Reset All Settings</h3>
                <p><b>⚠️ Warning:</b> This section resets ALL plugin settings to their default values.</p>
                <ul>
                    <li><b>'Reset All Settings to Defaults' button</b> - Resets all HellaFusion settings including file paths, timeouts, pause settings, and all other configurations. This action cannot be undone. Use with caution!</li>
                </ul>

                <h3>💡 Pause at Transition Tips:</h3>
                <ul>
                    <li><b>Nozzle Changes:</b> Enable pause at transitions where you want to change nozzles. Make sure to set nozzle lengths correctly in Expert Settings.</li>
                    <li><b>Filament/Color Changes:</b> Perfect for multi-color prints without an MMU. Pause, swap filament, purge, resume.</li>
                    <li><b>Material Changes:</b> Switch between compatible materials (e.g., PLA to PETG, or add TPU sections).</li>
                    <li><b>Custom Gcode:</b> Each transition can have unique pause gcode. Use 'Pause Settings' to customize per transition, or 'Apply to All' for consistency.</li>
                    <li><b>Park Position:</b> Default is X0 Y0. Edit the G0 command in pause gcode to match your printer's safe park position.</li>
                    <li><b>Purge Amount:</b> Default purge is E35. Adjust based on your nozzle size and material (larger nozzles or color changes need more).</li>
                    <li><b>Firmware Compatibility:</b> M0 (pause) works with most firmware. If your printer uses M25 or other pause commands, edit the pause gcode accordingly.</li>
                </ul>
            """
        }
    }
