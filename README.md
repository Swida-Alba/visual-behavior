# Visual Behavior Control System

A comprehensive system for delivering high-frequency visual stimuli and analyzing behaviors of Drosophila (fruit flies). This controller allows precise timing of visual stimuli coordinated with hardware control for behavioral experiments.

## Features

- **High-frequency video stimulus delivery** with precise timing
- **Hardware control via Arduino**:
  - LED control (ON/OFF, timed, pulsing)
  - Air pump and valve control
  - Odor valve control
  - Shock pulse delivery
- **Interactive command interface** with:
  - Real-time commands
  - Command series execution (chaining multiple commands)
  - Command shortcuts
  - Protocol creation and playback
- **Detailed experimental logging**
- **Customizable stimuli**
- **Timing precision** with dynamic ISI adjustments

## Requirements

### Hardware
- Arduino board (Arduino Uno recommended)
- A computer with dual monitors (recommended for visual stimulus presentation)
- Customized hardware setup with:
  - LEDs connected to Arduino
  - Solenoid valves (optional)
  - Air pump (optional) 
  - Shock delivery system (optional)

### Software
- Python 3.6+
- Required Python packages (see below)

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/visual-behavior.git
   cd visual-behavior
   ```

2. Set up your environment:

   **Option A: Using Conda (recommended)**
   
   Create and activate a new conda environment:
   ```
   conda create -n visual-behavior python=3.9
   conda activate visual-behavior
   ```
   
   Install the required packages from `requirements.txt`:
   ```
   pip install -r requirements.txt
   ```
   
   Or with conda for packages available in conda-forge:
   ```
   conda install -c conda-forge --file requirements.txt
   pip install moviepy==1.0.3  # Specific version required
   ```

   **Option B: Using pip**
   
   Install the required Python packages:
   ```
   pip install -r requirements.txt
   ```

3. Connect Arduino with appropriate firmware loaded.

## Quick Start

1. Navigate to the controller directory:
   ```
   cd controller_2_1_1
   ```

2. Run the default configuration:
   ```
   python play.py
   ```

3. Use the interactive command interface to control stimuli.

## Custom Configuration

Edit the `play.py` file to customize your experiment setup:

```python
from StimulationAssistant import StimController

player = StimController(
    video_dir='path/to/your/video/files',
    stim_name='r/v',  # Customize stimulus naming
    stimulus='20',    # Default stimulus to use
    LED_retention=2000,  # LED retention time in ms
    video_retention=1000,  # Video retention time in ms
    # Add other parameters as needed
)

player.start_journey()
```

## Command Reference

The system provides numerous commands for interactive control:

- `v` - Deliver a single video stimulus
- `v[number]` - Deliver video stimulus multiple times (e.g., `v5` for 5 times)
- `r` - Toggle red LED on/off
- `rX` - Turn on LED for X seconds (e.g., `r5` for 5 seconds)
- `p` - Deliver LED pulses
- `t` - Coordinated LED and video stimulation
- `stim` or `r/v` - Update stimulus value
- `pump` - Toggle air pump on/off
- `air` - Toggle air valve open/closed
- `odor_a` - Toggle odor A valve open/closed
- `odor_b` - Toggle odor B valve open/closed
- `shock` - Toggle shock pulses on/off
- `trig` - Send trigger signal
- `isiX` - Wait for X seconds (e.g., `isi5` for 5 seconds)
- `load` - Run available local protocol files
- `h` or `help` - Show help information
- `q` - Quit the program

### Advanced Commands

- **Command chaining** with `>` operator: `r5 > isi2 > p`
- **Command repetition** with parentheses and `*`: `(r2 > isi1) * 5`
- **Command shortcuts**: `test_odor <- pump:on > odor_a:on > isi5 > odor_a:off > pump:off`

## Folder Structure

- `controller_2_1_1/` - Main controller code
  - `StimulationAssistant.py` - Core controller class
  - `stimfunc.py` - Helper functions for stimulation
  - `play.py` - Example configuration
- `looming_videos/` - Default location for video stimuli
- `Jail/` - Default location for log files

## Troubleshooting

- **Arduino connection issues**: Make sure the Arduino is properly connected and has the correct firmware loaded.
- **Serial port errors**: Try restarting the program. If the error persists, check your Arduino connection.
- **Video playback issues**: Ensure the video path is correctly set and video files are in the proper format.
- **Performance problems**: Try closing other resource-intensive applications to ensure smooth video playback.
