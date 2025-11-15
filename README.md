# 🔥 HellaFusion Plugin for Cura

**Advanced Multi-Quality 3D Printing Made Easy**

HellaFusion revolutionizes your 3D printing workflow by enabling **dynamic quality switching** within a single print job. Print your models with different quality profiles at different heights, automatically combined into one seamless gcode file.

## ✨ Why HellaFusion?

Transform your 3D printing strategy with intelligent quality fusion:

🚀 **Speed + Quality**: Draft mode for hidden sections, fine detail where it matters  
🏗️ **Structural Optimization**: Heavy infill for bases, lightweight for tops  
🎯 **Material Efficiency**: Perfect balance of strength, speed, and material usage  
⚡ **Advanced Automation**: Intelligent layer alignment and seamless transitions  
🧠 **Smart Calculations**: Automatic layer height adjustments for perfect alignment  

## How It Works

HellaFusion uses advanced fusion technology to solve the multi-quality printing challenge:

1. **Intelligent Slicing**: Your model is sliced multiple times with different quality profiles
2. **Smart Extraction**: Relevant height sections are precisely extracted from each gcode
3. **Advanced Fusion**: Sections are seamlessly combined with intelligent transition management
4. **Perfect Alignment**: Automatic layer height adjustments ensure perfect layer-to-layer alignment

## Based On

This plugin is based on the excellent work of:
- **GregValiant (Greg Foresi)** - Original "Gcode Splice At Height" post-processing script
- **HellAholic** - Auto Slicer plugin architecture and UI patterns

## 🚀 Key Features

### **Advanced Fusion Technology**
- 🔄 **Dynamic Quality Switching**: Unlimited height transitions with different quality profiles
- 🎯 **Intelligent Layer Alignment**: Automatic initial layer height adjustments for perfect layer fusion
- ⚡ **Smart Transition Detection**: Calculates optimal transition points with minimal visual artifacts
- 🧮 **Precision Calculations**: Advanced algorithms ensure seamless layer-to-layer continuity

### **Professional Workflow**
- 🎨 **Complete Profile Support**: Compatible with all Cura quality profiles and custom user profiles
- 🏷️ **Intent Integration**: Full support for Engineering, Visual, and Draft intents
- 📊 **Real-Time Progress**: Live status updates and detailed progress tracking
- 💾 **Session Persistence**: Intelligent settings memory across sessions

### **User Experience**
- 🖱️ **Intuitive Interface**: Clean, modern UI with comprehensive help system
- ⚠️ **Smart Validation**: Real-time error detection and helpful guidance
- 🔧 **Advanced Configuration**: Customizable timeouts and processing options
- 📋 **Detailed Logging**: Comprehensive processing logs for troubleshooting

## 📦 Installation

### Quick Install
1. **Download** the `hellafusionplugin` folder from the repository
2. **Copy** to your Cura plugins directory:
   - **Windows**: `%APPDATA%\cura\<version>\plugins\`
   - **macOS**: `~/Library/Application Support/cura/<version>/plugins/`
   - **Linux**: `~/.local/share/cura/<version>/plugins/`
3. **Restart Cura** completely
4. **Access** via `Extensions` → `HellaFusion` 🔥

### Verify Installation
- Look for "HellaFusion" in the Extensions menu
- Plugin appears with a fire emoji icon
- Help system accessible via the "?" button in the interface

## 🎮 Usage Guide

### 🚀 Quick Start Fusion Workflow

1. **🏗️ Load Model**: Import your STL/3MF into Cura as usual
2. **🔥 Launch HellaFusion**: `Extensions` → `HellaFusion` 
3. **🎯 Define Fusion Points**: Click "Add Transition" for each quality change height
4. **📏 Set Heights**: Enter Z-heights (mm) where you want quality transitions
5. **🎨 Choose Profiles**: Select different quality profiles for each section
6. **💾 Set Destination**: Choose output folder for your fused gcode
7. **🧮 Calculate (Recommended)**: Click "Calculate Transitions" for optimal fusion
8. **⚡ Start Fusion**: Hit "Start Splicing" to create your multi-quality masterpiece!

### Understanding Sections

- **Section 1**: From build plate (Z=0) to first transition height
- **Section 2**: From first transition to second transition
- **Section N**: From previous transition to top of model

Each section can have its own quality profile with different:
- Layer height
- Print speed
- Infill percentage
- Support settings
- And any other Cura settings

### Transition Heights

- Transitions occur at specific Z heights in your model
- Heights are in millimeters from the build plate
- The plugin automatically adds the configured layer height to ensure transitions happen at actual layer boundaries
- Example: If you enter 10mm and your layer height is 0.2mm, the transition will occur at or just after 10mm

## Example Use Cases

### 🏺 Example 1: Speed + Quality Fusion
**Model**: Decorative vase (200mm tall)
- **Section 1** (0-100mm): Draft profile → 0.3mm layers, high speed
- **Fusion Point** at 100mm: Seamless quality transition
- **Section 2** (100-200mm): Fine profile → 0.1mm layers, precision speed
- **Result**: ⚡ Fast hidden base + ✨ Beautiful detailed top

### 🗿 Example 2: Structural Optimization
**Model**: Tall figurine (150mm)
- **Section 1** (0-50mm): Heavy infill profile → 100% infill for stability
- **Fusion Point** at 50mm: Material efficiency transition
- **Section 2** (50-150mm): Lightweight profile → 20% infill
- **Result**: 🏗️ Stable foundation + 🪶 Lightweight upper structure

### 🏢 Example 3: Multi-Purpose Fusion
**Model**: Architectural model (80mm)
- **Section 1** (0-30mm): Engineering intent → Dimensional accuracy
- **Section 2** (30-60mm): Visual intent → Surface quality perfection
- **Section 3** (60-80mm): Draft intent → Speed optimization
- **Result**: 🎯 Each section optimized for its specific purpose

## Technical Details

### How It Works

1. **Profile Switching**: The plugin changes Cura's active profile for each section
2. **Multiple Slicing**: Your model is sliced once for each section
3. **Gcode Extraction**: Each sliced gcode is parsed to extract the relevant section
4. **Transition Calculation**: At each transition:
   - Current XYZ position is recorded from the ending section
   - Starting XYZ position is extracted from the beginning section
   - Movement and reset code is calculated to bridge the gap
   - E-axis (extrusion) is synchronized to prevent under/over-extrusion
5. **Gcode Combining**: Sections are combined with transition code inserted
6. **Output**: A single gcode file ready to print

### Transition Code

At each transition, the plugin inserts:
- **Z-hop movement**: Raises nozzle to prevent collision
- **XY movement**: Moves to starting position of next section
- **Z adjustment**: Sets Z height accounting for layer height changes
- **E reset**: Synchronizes extrusion position (handles retraction state)

### Limitations

- **Print Sequence**: Not compatible with "One-at-a-Time" mode
- **Adaptive Layers**: Can work but requires careful height selection
- **Z-hops**: The plugin accounts for Z-hops but they can affect transition heights
- **Pause at Height**: Can be used but may interfere with transition detection
- **Multi-Extruder**: Currently optimized for single-extruder printing

## Configuration

### Settings Saved

The plugin saves the following settings between sessions:
- Model file path
- Destination folder
- Slice timeout
- Transition definitions (heights and profiles)

### Slice Timeout

- Default: 300 seconds (5 minutes)
- Range: 30-3600 seconds
- Purpose: Maximum time to wait for each slicing operation
- Recommendation: Increase for complex models

## Troubleshooting

### "No quality profiles available"
- Ensure you have an active printer configuration in Cura
- Check that quality profiles exist for your current machine/material combination

### "Failed to load model"
- Verify the model file exists and is a valid STL/3MF file
- Check file permissions
- Try loading the file in Cura manually first

### "Slicing timeout"
- Increase the timeout value
- Simplify the model or reduce quality settings
- Check if Cura can slice the model normally

### "Transition heights above model"
- Ensure all transition heights are below the model's maximum Z
- Check that you're using the correct units (mm)

### "Failed to combine gcode"
- Review the log for specific error messages
- Verify all sections sliced successfully
- Check destination folder has write permissions

## Development

### File Structure

```
hellafusionplugin/
├── __init__.py                 # Plugin registration
├── plugin.json                 # Plugin metadata
├── HellaFusion.py            # Main extension class
├── HellaFusionController.py  # Business logic
├── HellaFusionDialog.py      # UI dialog
├── HellaFusionJob.py         # Background processing job
├── HellaFusionLogic.py       # Core splicing algorithms
├── PluginConstants.py         # UI styling constants
└── README.md                  # This file
```

### Contributing

Contributions are welcome! Areas for improvement:
- Multi-extruder support
- Support for more transition types (temperature, speed, etc.)
- Enhanced error recovery
- Better visualization of transitions
- Gcode preview integration

## License

This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

## 🙏 Credits & Acknowledgments

### Original Innovators
- **🧠 GregValiant (Greg Foresi)**: Pioneer of gcode splicing algorithms and transition logic
- **⚡ HellAholic**: AutoSlicer plugin architecture mastermind and UI design patterns
- **🛠️ Cura Development Team**: Cura API and extension framework foundation

### 🔥 HellaFusion Evolution
**HellaFusion** represents the next evolution of multi-quality 3D printing, building upon the solid foundation of these pioneers while introducing revolutionary fusion technology.

## 📋 Version History

### 🚀 1.0.0 (2025) - "Fusion Genesis"
- ✨ Revolutionary multi-quality fusion technology
- 🎯 Unlimited transition support with intelligent alignment
- 🧮 Advanced calculation engine for optimal layer fusion
- 🎨 Modern UI with comprehensive help system
- 💾 Intelligent settings persistence and session management
- ⚡ Real-time progress tracking and validation

## 🆘 Support & Community

### Getting Help
1. 📖 **Check the built-in help system** (? button in HellaFusion interface)
2. 🔍 **Review troubleshooting section** above
3. 📋 **Check Cura's log files** for detailed error information
4. 🐛 **Report issues** with complete setup details and log files

### 🤝 Contributing
The future of advanced 3D printing is collaborative! Areas for enhancement:
- 🔧 Multi-extruder fusion support
- 🌡️ Temperature and speed transition optimization
- 🛡️ Enhanced error recovery systems
- 📊 Advanced visualization and preview features
- 🔗 Integration with Cura's gcode preview

## ✨ The HellaFusion Promise

**HellaFusion** transforms the impossible into the inevitable - enabling 3D printing workflows that were previously unachievable. Join the fusion revolution and unlock the true potential of your 3D printer!

---

*Made with 🔥 for the 3D printing community*
