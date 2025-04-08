import os
import re
import cv2
import time
import numpy as np
import stimfunc as playstim
from dataclasses import dataclass
from datetime import datetime

@dataclass
class StimController:
    script_path = os.path.dirname(os.path.abspath(__file__))
    '''current absolute path of the controller'''

    video_dir: str = os.path.join(script_path,'video_stimuli')
    '''absolute or relative path to the video stimulus files'''

    video_format: str = '.mp4'
    '''format of the video files'''

    protocol_dir: str = os.path.join(script_path,'stim_protocols')
    '''path to the protocol files'''

    protocol_saveas: str = os.path.join(protocol_dir, 'autosaved_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt')
    '''path of the protocol file to save the current experiment sessions'''

    video_retention: int = 1000
    '''retention time (ms) of the last frame on the screen'''

    stimulus: str = '80'
    '''value of stimulus, e.g. r/v value, or any other given name of the stimulus file in the video_dir'''

    stim_name: str = 'r/v'
    '''customized name of the stimulus, to be displayed in the log file and interactive command line'''

    LED_retention: int = 5000
    '''retention time (ms) of the LEDs in the video-LED timer mode'''

    background_img = np.full((500,500,3),255,dtype=np.uint8)
    '''path of the background image of the video player'''

    save_path: str = ''
    '''path to save the current log and other necessary files'''

    ser: str = ''
    '''serial port object, if the serial port is connected'''

    board_type: str = 'Arduino Uno'
    '''type of the serial port board to connect to'''
    
    baud_rate: int = 9600
    '''baud rate of the serial port, default to 9600'''

    window_bg: str = 'background'
    '''window name of the background image'''

    window_video: str = 'player'
    '''window name of the video player'''

    log_name: str = ''
    '''name of the log file to save the current event logs, added as a suffix to the file name'''

    videoLED_timer: int = 0
    '''default value of the LED&video timer (ms)'''

    update_timer: bool = True
    '''whether to update the LED&video timer'''

    pulse_span: float = 5.0
    '''span time of the pulse in "p" mode'''

    pulse_frequency: int = 2
    '''pulsing frequency in "p" mode'''
    
    pulse_width: int = 50
    '''pulse width in "p" mode'''

    update_pulse: bool = True
    '''whether to update the pulse parameters: pulse_span, pulse_frequency, pulse_width, when entering "p" mode'''

    play_times: int = 0
    '''number of times to play stimulus video'''

    well_times: int = 3
    '''number of times to say "well"'''

    u_time: int = 3
    '''retention time of "u"'''
    
    shut_backgroud: bool = False
    '''set to True to shutdown the video player window'''

    pump_state: bool = False
    '''state of the air pump (True=on, False=off)'''
    
    pump_value: int = 200
    '''PWM value for controlling the pump (0-255)'''
    
    shock_state: bool = False
    '''state of shock pulses (True=on, False=off)'''
    
    air_state: bool = False
    '''state of the air valve (True=open, False=closed)'''
    
    odor_a_state: bool = False
    '''state of the odor A valve (True=open, False=closed)'''
    
    odor_b_state: bool = False
    '''state of the odor B valve (True=open, False=closed)'''
    
    attr_unit = { # avaible attributes and corresponding units
        'videoLED_timer':  'ms',
        'LED_retention':   'ms',
        'video_retention':  'ms',
        'well_times':      'times',
        'u_time':          's',
        'update_timer':    '',
        'update_pulse':    '',
        'pulse_span':      's',
        'pulse_frequency': 'Hz',
        'pulse_width':     'ms',
        'stimulus':        '',
        'pump_value':      '(0-255)',
    }

    # Add new attributes for shortcuts
    shortcuts_file: str = os.path.join(script_path, 'command_shortcuts.txt')
    '''path to the file storing command shortcuts'''
    
    shortcuts: dict = None
    '''dictionary of saved command shortcuts'''

    def __post_init__(self):
        '''update the parameters and initialization'''
        self.t_today: str = datetime.now().strftime('%Y%m%d')
        '''date running the experiment, as part of the file path to save the current log'''
        
        self.prompt: str = '\nPress <Enter> to play video; input \033[34m"help" ("h")\033[0m for help info, "q" to terminate;\n: '
        '''instructions of input command'''
        
        self.mutable_attrs = list(self.attr_unit.keys()) # mutable attributes in running sessions
        
        if not self.protocol_dir:
            self.protocol_dir =  os.path.join(self.script_path, 'stim_protocols')
        if not self.protocol_saveas:
            self.protocol_saveas = os.path.join(self.protocol_dir, 'autosaved_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.txt')

        
        # initializing serial port
        if not self.ser:
            self.ser = playstim.SetUpSerialPort(board_type=self.board_type, baud_rate=self.baud_rate)
        self.LED_state = 0
        
        # building the save path of log files
        if not self.save_path:
            self.save_path = os.path.abspath(os.path.join(self.script_path, '..', 'Jail', self.t_today))
        if not os.path.exists(self.save_path): os.makedirs(self.save_path)
        print(f'Current data folder: {self.save_path}')
        
        # loading stimulus videos and background image
        if not os.path.isabs(self.video_dir):
            self.video_dir = os.path.abspath(os.path.join(self.script_path, self.video_dir))
        self.video_files = []
        for file in os.listdir(self.video_dir):
            if file.endswith(self.video_format):
                self.video_files.append(file)
            elif file.startswith('bg_'):
                self.background_img = cv2.imread(os.path.join(self.video_dir, file))
        if not self.shut_backgroud:
            self.window_bg = playstim.initialize_window(self.background_img, window=self.window_bg) # initializing palyer background
        self.video_dict = dict()
        for i in range(len(self.video_files)):
            # the video name should be as short and specific as possible
            self.video_dict.update({self.video_files[i].split('.')[0]: playstim.read_video(os.path.join(self.video_dir, self.video_files[i]))})
            print(f'\rLoading stimulus videos from: {self.video_dir} ...loaded {i+1}/{len(self.video_files)}', end='   ')
        print()
        self.valid_stim = list(self.video_dict.keys()) # available stimulus name of stimulus videos

        if not self.stimulus in self.valid_stim:
            print(f'\n\033[31mWarning: {self.stim_name} = {self.stimulus} is not available, please change "stimulus" to one of the available values\033[0m')
            self.stimulus = self.valid_stim[0]
            print(f'stimulus is set to {self.stimulus}\n')
        print(f'Available {self.stim_name} values: ', end='')
        print(*self.valid_stim, sep=', ')
        
        self.frms, self.read_fps = self.video_dict[self.stimulus]
        if not self.shut_backgroud:
            self.window_video = playstim.initialize_window(self.frms[0], window=self.window_video) # initialize the video player window
            print(f'Current {self.stim_name} = {self.stimulus}')
        
        
        # checking the existed log files and building new log file if required
        existed_logfiles = playstim.get_existed_files(self.save_path,prefix = self.t_today)
        print('Existed log files:')
        for file in existed_logfiles:
            print('\t'+file)
        print()
        if self.log_name:
            self.log_name = self.t_today + '_' + self.log_name + '_log.txt'
        else:
            self.log_name = input('\033[34mPlease input the custom file name or press <Enter> directly: \033[0m')
            if self.log_name:
                self.log_name = self.t_today + '_' + self.log_name + '_log.txt'
            else:
                self.log_name = self.t_today + '_log.txt'
        print(f'Log file will be saved as: {self.log_name}')
        
        self.log_file = os.path.join(self.save_path, self.log_name)
        
        # Initialize shortcuts dictionary
        self.shortcuts = {}
        self.load_shortcuts()

    def load_shortcuts(self):
        """Load command shortcuts from the shortcuts file"""
        if not os.path.exists(self.shortcuts_file):
            # Create the file if it doesn't exist
            with open(self.shortcuts_file, 'w') as f:
                f.write("# Command shortcuts file\n")
                f.write("# Format: shortcut_name <- command > command > command\n\n")
            return
            
        try:
            # Clear existing shortcuts before loading
            self.shortcuts = {}
            invalid_shortcuts = []
            
            with open(self.shortcuts_file, 'r') as f:
                lines = f.readlines()
                
            for line in lines:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                    
                # Parse shortcut name and commands
                if '<-' in line:
                    parts = line.split('<-', 1)
                    shortcut_name = parts[0].strip()
                    command_series = parts[1].strip()
                    
                    # Skip reserved names (but don't error if already in shortcuts)
                    if shortcut_name in ['h', 'help', 'q', 'v', 'p', 't', 'well', 'u', 'run', 'load', 'trig',
                                        'stim', 'set', 'show', 'r', 'isi', 'pump', 'shock', 'air',
                                        'odor_a', 'odor_b', 'stop'] or shortcut_name == self.stim_name:
                        invalid_shortcuts.append((shortcut_name, f"Reserved command name"))
                        continue
                        
                    # Validate the command series
                    valid = True
                    if '(' in command_series and '*' in command_series:
                        # Handle repetition patterns
                        pattern = r'\((.*?)\)\s*\*\s*(\d+)'
                        matches = re.findall(pattern, command_series)
                        
                        # For each match, validate inner commands
                        for match_content, _ in matches:
                            # Before full validation, check for basic commands inside
                            valid_inner = True
                            for inner_cmd in match_content.split('>'):
                                inner_cmd = inner_cmd.strip()
                                # Skip validation for shortcuts within the commands
                                if inner_cmd in self.shortcuts:
                                    continue
                                # Basic validation for built-in commands
                                if not self.is_basic_command_valid(inner_cmd):
                                    valid_inner = False
                                    break
                            
                            if not valid_inner:
                                valid = False
                                break
                    else:
                        # Normal command series
                        for cmd in command_series.split('>'):
                            cmd = cmd.strip()
                            # Skip validation for shortcuts within the commands
                            if cmd in self.shortcuts:
                                continue
                            # Basic validation for built-in commands
                            if not self.is_basic_command_valid(cmd):
                                valid = False
                                break
                    
                    # Add valid shortcuts to dictionary
                    if valid:
                        self.shortcuts[shortcut_name] = command_series
                    else:
                        invalid_shortcuts.append((shortcut_name, "Contains invalid commands"))
            
            # Report invalid shortcuts if any found
            if invalid_shortcuts and len(invalid_shortcuts) > 0:
                print("\n\033[33mWarning: The following shortcuts were not loaded because they are invalid:\033[0m")
                for name, reason in invalid_shortcuts:
                    print(f"  - \033[33m{name}\033[0m: {reason}")
                print()
                
        except Exception as e:
            print(f"Error loading shortcuts: {e}")
    
    def is_basic_command_valid(self, command):
        """
        Basic validation of commands for shortcut loading
        Less strict than full validation to allow for parameter values
        
        Parameters:
            command (str): Command to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not command:
            return True  # Empty command is valid (play video)
            
        # Simple command validation for basic commands
        if command == 'q' or command == 'h' or command == 'v' or command == 'p' or \
           command == 't' or command == 'well' or command == 'u' or command == 'run' or \
           command == 'load' or command == 'trig' or command == self.stim_name or \
           command == 'stim' or command.startswith('help') or \
           command == 'pump' or command == 'shock' or command == 'air' or \
           command == 'odor_a' or command == 'odor_b' or command == 'stop' or \
           command == 'shortcuts':
            return True
            
        # Command with parameters
        if command[0] == 'r' and command != 'run':
            # r commands (LED control)
            if len(command) == 1 or command[1:].replace('.', '').isnumeric():
                return True
        elif command.startswith('set:'):
            # Not doing full validation, just basic format check
            return '=' in command.split(':', 1)[1].replace(' ', '')
        elif command.startswith('show:'):
            # Similarly simple validation for show
            return len(command.split(':')) == 2 and command.split(':', 1)[1].strip()
        elif command.lower().startswith('isi'):
            # ISI commands
            return len(command) > 3 and command[3:].replace('.', '').isnumeric()
        # Validate pump commands
        elif command.startswith('pump:'):
            if command in ['pump:on', 'pump:off']:
                return True
            if command.startswith('pump:value:'):
                value_str = command[11:]
                return value_str.isnumeric() and 0 <= int(value_str) <= 255
        # Validate other device commands
        elif command.startswith('shock:'):
            return command in ['shock:on', 'shock:off']
        elif command.startswith('air:'):
            return command in ['air:on', 'air:off']
        elif command.startswith('odor_a:'):
            return command in ['odor_a:on', 'odor_a:off']
        elif command.startswith('odor_b:'):
            return command in ['odor_b:on', 'odor_b:off']
                
        # If we get here, command format is not recognized
        return False
    
    def save_shortcut(self, shortcut_name, command_series):
        """
        Save a new command shortcut
        
        Parameters:
            shortcut_name (str): Name of the shortcut
            command_series (str): Series of commands separated by '>'
            
        Returns:
            int: 0 if successful, 1 if error
        """
        # Validate shortcut name
        if not self.validate_shortcut_name(shortcut_name):
            return 1
            
        # Validate command series
        if not self.validate_command_series(command_series):
            return 1
            
        # Add to shortcuts dictionary
        self.shortcuts[shortcut_name] = command_series
        
        # Save to file
        try:
            # Read all existing shortcuts and comments
            existing_content = []
            max_name_length = 20  # Default padding length
            
            if os.path.exists(self.shortcuts_file):
                with open(self.shortcuts_file, 'r') as f:
                    existing_content = f.readlines()
                
                # Calculate maximum name length for proper alignment
                for line in existing_content:
                    line = line.strip()
                    if line and not line.startswith('#') and '<-' in line:
                        name = line.split('<-')[0].strip()
                        max_name_length = max(max_name_length, len(name) + 2)  # +2 for extra padding
            
            # Format the new shortcut with proper alignment
            formatted_shortcut = f"{shortcut_name:<{max_name_length}} <- {command_series}\n"
                
            # Add the new shortcut
            with open(self.shortcuts_file, 'w') as f:
                # Write header if file was empty
                if not existing_content:
                    f.write("# Command shortcuts file\n")
                    f.write("# Format: shortcut_name <- command > command > command\n\n")
                    
                # Write existing content
                for line in existing_content:
                    # Don't rewrite lines that contain the same shortcut name
                    if not (line.strip() and not line.strip().startswith('#') and 
                            line.split('<-')[0].strip() == shortcut_name):
                        f.write(line)
                
                # Add a newline if the last line doesn't end with one
                if existing_content and not existing_content[-1].endswith('\n'):
                    f.write('\n')
                    
                # Add an extra newline if the last line isn't already blank
                if existing_content and existing_content[-1].strip():
                    f.write('\n')
                    
                # Write the new shortcut
                f.write(formatted_shortcut)
                
            print(f"Shortcut '{shortcut_name}' saved successfully")
            return 0
        except Exception as e:
            print(f"Error saving shortcut: {e}")
            return 1
    
    def validate_shortcut_name(self, name):
        """
        Validate if the shortcut name is valid
        
        Parameters:
            name (str): Name of the shortcut
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Check if name already exists as a shortcut
        if name in self.shortcuts:
            print(f"Shortcut name '{name}' already exists")
            return False
            
        # Check if name is a built-in command
        if name in ['h', 'help', 'q', 'v', 'p', 't', 'well', 'u', 'run', 'load', 'trig',
                    'stim', 'set', 'show', 'r', 'isi', 'pump', 'shock', 'air',
                    'odor_a', 'odor_b', 'stop'] or name == self.stim_name:
            print(f"Cannot use '{name}' as shortcut name because it's a built-in command")
            return False
            
        # Check for valid characters (letters, numbers, underscore)
        if not re.match(r'^[a-zA-Z0-9_]+$', name):
            print(f"Invalid shortcut name '{name}'. Use only letters, numbers, and underscore")
            return False
            
        return True
    
    def validate_command_series(self, command_series):
        """
        Validate if all commands in the command series are valid
        
        Parameters:
            command_series (str): Series of commands separated by '>'
            
        Returns:
            bool: True if all commands are valid, False otherwise
        """
        # First check for repetition patterns and handle them specially
        if '(' in command_series and '*' in command_series:
            # Temporarily replace repetition patterns with placeholder
            pattern = r'\((.*?)\)\s*\*\s*(\d+)'
            matches = re.findall(pattern, command_series)
            
            # For each match, validate the commands inside separately
            for match_content, repeat_count in matches:
                if not self.validate_command_series(match_content):
                    return False
                    
            # Replace patterns with placeholders for main validation
            modified_cmd = re.sub(pattern, 'valid_placeholder', command_series)
            # Validate the rest of the command string
            commands = modified_cmd.split('>')
        else:
            # Normal command series without repetition
            commands = command_series.split('>')
        
        for cmd in commands:
            cmd = cmd.strip()
            # Skip placeholder from repetition pattern
            if cmd == 'valid_placeholder':
                continue
                
            # Special case for shortcuts in command series
            if cmd in self.shortcuts:
                continue
            
            validated_cmd = self.validify_command(cmd)
            if validated_cmd is None:
                print(f"Invalid command in series: '{cmd}'")
                return False
                    
        return True

    def execute_shortcut(self, shortcut_name):
        """
        Execute a saved command shortcut
        
        Parameters:
            shortcut_name (str): Name of the shortcut
            
        Returns:
            int: 0 if successful, 1 if error
        """
        if shortcut_name not in self.shortcuts:
            print(f"Shortcut '{shortcut_name}' not found")
            return 1
            
        command_series = self.shortcuts[shortcut_name]
        print(f"Executing shortcut '{shortcut_name}': {command_series}")
        
        # Fully expand all nested shortcuts first
        expanded_series = self.expand_shortcuts(command_series)
        
        # Handle repetition patterns in the fully expanded shortcuts
        if '(' in expanded_series and '*' in expanded_series:
            return self.parse_wrapped_commands(expanded_series)
        else:
            # Execute the expanded command series
            return self.parse_combined_commands(expanded_series)
    
    def expand_shortcuts(self, command_series):
        """
        Expand shortcuts within a command series recursively
        
        Parameters:
            command_series (str): Series of commands separated by '>'
            
        Returns:
            str: Expanded command series with shortcuts replaced by their commands
        """
        # First, split by '>' to get individual commands
        commands = command_series.split('>')
        result = []
        
        for cmd in commands:
            cmd = cmd.strip()
            if cmd in self.shortcuts:
                # Recursively expand nested shortcuts - this is the key improvement
                expanded = self.expand_shortcuts(self.shortcuts[cmd])
                # The expanded result could contain multiple commands, so we need to split again
                result.extend([c.strip() for c in expanded.split('>')])
            else:
                # Check if this is a repetition pattern command
                if cmd.startswith('(') and ')' in cmd and '*' in cmd:
                    # Handle repetition patterns inside shortcuts
                    pattern = r'\((.*?)\)\s*\*\s*(\d+)'
                    match = re.match(pattern, cmd)
                    if match:
                        inner_cmds = match.group(1).strip()
                        repeat_count = int(match.group(2))
                        # Recursively expand the inner commands
                        expanded_inner = self.expand_shortcuts(inner_cmds)
                        # Add the expanded repeated sequence
                        repeated_cmds = " > ".join([expanded_inner] * repeat_count)
                        result.extend([c.strip() for c in repeated_cmds.split('>')])
                    else:
                        result.append(cmd)
                else:
                    result.append(cmd)
        
        # Join all commands with proper separator
        return " > ".join(result)
    
    def parse_wrapped_commands(self, cmd_series):
        """
        Parse and execute a series of commands that may include repetition patterns
        Supports syntax like: "cmd1 > cmd2 > (cmd3 > cmd4) * 5 > cmd5"
        
        Parameters:
            cmd_series (str): Command series with potential repetition patterns
        
        Returns:
            int: 0 if successful, 1 if error
        """
        # First, fully expand any shortcuts to get basic commands
        expanded_series = self.expand_shortcuts(cmd_series)
        
        # Then expand repetition patterns
        fully_expanded = self.expand_repetition_patterns(expanded_series)
        
        # Finally process the fully expanded series
        return self.parse_combined_commands(fully_expanded)

    def expand_repetition_patterns(self, cmd_series):
        """
        Expand repetition patterns in command series
        
        Parameters:
            cmd_series (str): Command string with potential patterns like "(cmd1 > cmd2 > cmd3) * 5"
        
        Returns:
            str: Expanded command string with all patterns resolved
        """
        result = cmd_series
        
        # Handle patterns like "(cmd1 > cmd2 > cmd3) * 5"
        pattern = r'\((.*?)\)\s*\*\s*(\d+)'
        while re.search(pattern, result):
            match = re.search(pattern, result)
            
            # Extract the commands inside parentheses and repetition count
            commands_inside = match.group(1).strip()
            repeat_count = int(match.group(2))
            
            # Make sure any shortcuts inside are fully expanded
            expanded_inside = self.expand_shortcuts(commands_inside)
            
            # Create the expanded sequence
            expanded = " > ".join([expanded_inside] * repeat_count)
            
            # Replace the pattern with the expanded sequence
            result = result[:match.start()] + expanded + result[match.end():]
        
        # Remove any extra spaces around '>'
        result = re.sub(r'\s*>\s*', ' > ', result)
        
        return result

    def show_attr(self,key_input):
        '''show the value of the attribute'''
        if key_input == 'show':
            for attr in self.mutable_attrs:
                print(f'\t{attr} = {getattr(self,attr)}')
        elif ':' in key_input:
            key_input = key_input.split(':')[1]
            attr = key_input
            if hasattr(self,attr):
                print(f'{attr} = {getattr(self,attr)}')
                return 0
            else:
                print(f'No attribute named {attr}!')
                return
    
    def update_mutable_attr(self,key_input):
        '''update the value of the attribute'''
        if ':' in key_input:
            key_input = key_input.split(':')[1]
        attr_val = key_input.replace(' ','')
        if '=' not in attr_val:
            print('Invalid input! Please input as "set:attribute=value"!')
            return
        attr = attr_val.split('=')[0]
        val = attr_val.split('=')[1]
        
        if not hasattr(self,attr):
            print(f'No attribute named {attr}!')
            print(f'Immediately mutable attributes: {self.mutable_attrs}')
            return
        elif attr == 'stimulus':
            return self.reset_stimulus(val)
        elif attr not in self.mutable_attrs:
            print(f'Attribute {attr} is not immediately mutable!')
            print(f'Immediately mutable attributes: {self.mutable_attrs}')
            return
        elif attr in ['LED_retention','video_retention','videoLED_timer','well_times','pulse_width']:
            if val.isnumeric():
                val = int(val)
            else:
                print(f'Invalid value for {attr}!')
                return
        elif attr in ['u_time','pulse_span','pulse_frequency']:
            if val.isnumeric():
                val = int(val)
            elif val.replace('.','').isnumeric():
                val = float(val)
            else:
                print(f'Invalid value for {attr}!')
                return
        elif attr in ['update_timer','update_pulse']:
            if val.lower() == 'true':
                val = True
            elif val.lower() == 'false':
                val = False
            elif val.isnumeric():
                val = bool(int(val))
            else:
                print(f'Invalid value for {attr}!')
                return
        setattr(self,attr,val)
        print(f'Current {attr} = {val} '+self.attr_unit[attr], type(getattr(self,attr)))
        return 0
    
    def say_well(self):
        if self.well_times:
            print('well ' * self.well_times)
        else:
            print('Well done!')
        return 0
    
    def say_u(self):
        umage = np.load(os.path.join(self.script_path, 'umage.npy'))
        uindow = playstim.initialize_window(img_to_show=umage,window='umage_uindow',window_size=(400,600),window_pos=(800,150),full_screen=False,always_on_top=True)
        cv2.waitKey(max(int(self.u_time * 1000),1))
        cv2.destroyWindow(uindow)
        return 0
        
    def terminate(self):
        '''terminate the current session'''
        playstim.LED_switch(self.LED_state,self.ser,self.log_file,turn_on=False)
        
        # Make sure to turn off pump and all valves
        if self.pump_state:
            playstim.pump_switch(self.pump_state, self.ser, self.log_file, turn_on=False)
        if self.shock_state:
            playstim.shock_switch(self.shock_state, self.ser, self.log_file, turn_on=False)
        if self.air_state:
            playstim.valve_switch('air', self.air_state, self.ser, self.log_file, turn_on=False)
        if self.odor_a_state:
            playstim.valve_switch('odor_a', self.odor_a_state, self.ser, self.log_file, turn_on=False)
        if self.odor_b_state:
            playstim.valve_switch('odor_b', self.odor_b_state, self.ser, self.log_file, turn_on=False)
            
        cv2.destroyAllWindows()
        if self.ser: self.ser.close()
        print('Sessions terminated.')
        if os.path.exists(self.protocol_saveas): print(f'Current protocol was saved as: {self.protocol_saveas}')
        return 0
    
    def deliver_video_command(self, key_input='v'):
        """
        Unified function to handle video delivery commands.
        - Input 'v' to deliver a single video.
        - Input 'v[number]' to deliver the video [number] times.
        """
        if key_input == 'v':  # Single video delivery
            print(f'{self.stim_name} = {self.stimulus}')
            real_fps, interval, t_play, t_end = playstim.play_video(
                self.frms, self.read_fps, self.window_video, retention_time=self.video_retention
            )
            playstim.write_video_log(
                self.log_file, real_fps, self.read_fps, self.stimulus, t_play, t_end, self.LED_state, duration=np.sum(interval) / 1000
            )
            if not self.shut_backgroud:
                self.window_video = playstim.initialize_window(self.frms[0])
        elif key_input.startswith('v') and key_input[1:].isnumeric():  # Video series delivery
            loop_times = int(key_input[1:])
            print(f'stimulus series: {loop_times} times')
            with open(self.log_file, 'a') as log:
                log.write(f'stimulus series: {loop_times} times\n\n')
            for i in range(loop_times):
                print(f'Playing video {i + 1}/{loop_times}')
                self.deliver_video_command('v')  # Recursive call for single video delivery
        else:
            print('Invalid input for video command. Use "v" or "v[number]".')
            return 1
        return 0
    
    def reset_stimulus(self, stim_new = None):
        if stim_new is None:
            stim_new = input(f'Please input the new {self.stim_name} (current {self.stim_name} = {self.stimulus}): ')
        if stim_new in self.valid_stim:
            self.stimulus = stim_new
            self.frms, self.read_fps = self.video_dict[self.stimulus]
            print(f'{self.stim_name} is reset to {self.stimulus}.')
            return 0
        else:
            print(f'Input stimulus name not available, please input a valid {self.stim_name} value in {self.valid_stim}.')
            return
    
    def LED_controller(self, key_input = 'r'):
        '''control the LED; switch on/off or set the ON time'''
        if key_input == 'r': # turn on/off the LED
            self.LED_state = playstim.LED_switch(self.LED_state,self.ser,self.log_file)
        elif key_input[1:].replace('.','').isnumeric(): # set the LED ON time if the LED is off
            LED_t = float(key_input[1:])
            playstim.LED_timer(self.LED_state,self.ser,self.log_file,timer=LED_t)
        else:
            print('Invalid input. "r" should be followed by a number to specify the LED ON time (s).')
            return
        return 0
    
    def LED_pulse_controller(self):
        '''control LED pulsing, including setting the pulsing span (s, float), frequency (Hz, float) and pulse width (ms, int)'''
        if playstim.LED_check(self.LED_state, self.ser) != 0: return
        if self.update_pulse:
            d_input = input('Please input the pulsing span (s): ')
            f_input = input('Please input the pulsing frequency (Hz): ')
            pw_input = input('Please input the pulse width (ms): ')
            if d_input.replace('.','').isnumeric() and f_input.replace('.','').isnumeric() and pw_input.isnumeric():
                self.pulse_span = float(d_input)
                self.pulse_frequency = float(f_input)
                if int(pw_input) < 2:
                    pw_input = 2
                    print(f'\033[33mPulse width is too small, set to 2 ms\033[0m')
                self.pulse_width = int(pw_input)
            else:
                print('Invalid input. Valid numbers are required!')
                return
        playstim.LED_pulse(self.LED_state,self.ser,self.log_file,duration=self.pulse_span,frequency=self.pulse_frequency,pulse_width=self.pulse_width)
        return 0
    
    def videoLED_coordination(self):
        '''
        Coordinated and timed LED and video stimuli
        not user-friendly enough, need to be improved
        '''
        if playstim.LED_check(self.LED_state, self.ser) != 0: return
        else:
            if self.update_timer:
                timer_input = input(f'\nPlease input the timer (s) or press <Enter> to use the latest timer ({self.videoLED_timer} ms)\npositive for LED->video playing, negative for video playing->LED: ')
                if timer_input != '':
                    if timer_input.replace('-','').replace('.','').isnumeric():
                        self.videoLED_timer = int(float(timer_input)*1000) # update timer and convert to ms
                    else:
                        print('Invalid input, please input a number.')
                        return
            video_time = len(self.frms) / self.read_fps + self.video_retention/1000
            print_timer = (self.LED_retention - self.videoLED_timer)/1000 - video_time
            playstim.LED_timer(self.LED_state, self.ser, self.log_file, timer=self.LED_retention/1000, delay=-self.videoLED_timer/1000, wait_for_feedback=False) # delay only works when greater than 0
            playstim.time_delay(self.videoLED_timer/1000,prefix='Waiting for stimulus:',suffix='s') # only works when the timer is positive
            self.deliver_video()
            if print_timer > 0: playstim.time_delay(print_timer,prefix='Waiting for LED END:',suffix='s')
        return 0
    
    def ClearSerialBuffer(self, print_flag=False):
        '''
        Check and process the serial buffer
        Handles warnings and state updates from Arduino instead of just clearing them
        '''
        if not self.ser:
            return
        lineNum = 0
        while self.ser.inWaiting() > 0:
            fb = self.ser.readline().decode()[:-1]
            lineNum += 1
            
            # Process important messages before clearing
            if fb.startswith("Warning:"):
                print(f'\033[33m{fb}\033[0m')
                if "Cannot open valve - Pump is OFF" in fb and hasattr(self, 'last_valve_attempted'):
                    setattr(self, self.last_valve_attempted + "_state", False)
            elif "valve OPEN" in fb:
                valve_name = fb.split(" ")[0].lower()
                if hasattr(self, f"{valve_name}_state"):
                    setattr(self, f"{valve_name}_state", True)
            elif "valve CLOSED" in fb or "All valves CLOSED" in fb:
                if "All valves CLOSED" in fb:
                    self.air_state = self.odor_a_state = self.odor_b_state = False
                else:
                    valve_name = fb.split(" ")[0].lower()
                    if hasattr(self, f"{valve_name}_state"):
                        setattr(self, f"{valve_name}_state", False)
            elif "Pump ON" in fb:
                self.pump_state = True
            elif "Pump OFF" in fb:
                self.pump_state = self.air_state = self.odor_a_state = self.odor_b_state = False
            elif print_flag:
                print(f'\033[30mCleared serial buffer -- line {lineNum}: {fb}\033[0m')
        
        if lineNum == 0 and print_flag:
            print('No info in serial buffer.')
        return 0

    def write_protocols(self, key_input, skip_isi = False):
        '''write current command to local protocol file'''
        # Skip automatic ISI recording if the command itself is an ISI command
        if hasattr(self, 't_last_stim') and not skip_isi:
            self.t_stim_end = time.time()
            t_interval = self.t_stim_end - self.t_last_stim
            self.t_last_stim = self.t_stim_end
            cmd_write = f'ISI {t_interval:.3f}'
            cmt_write = f'inter-stimulus interval: {t_interval:.3f} s'
            with open(self.protocol_saveas,'a') as f:
                f.write(cmd_write + ' '*(40-len(cmd_write)) + ' # ' + cmt_write + '\n\n')
        else:
            self.t_last_stim = time.time()
        
        # Initialize command and comment variables
        cmd_write = ''
        cmt_write = ''
        
        # Handle different command types
        if key_input == '':
            cmd_write = 'Play'
            cmt_write = 'playing video stimulus'
        elif key_input == 'v':
            cmd_write = 'Play ' + str(self.play_times)
            cmt_write = 'playing video for ' + str(self.play_times) + ' times'
        elif key_input == 'stim' or key_input == self.stim_name:
            cmd_write = f'{self.stim_name} ' + str(self.stimulus)
            cmt_write = f'set {self.stim_name} to {self.stimulus}'
        elif key_input[0] == 'r' and key_input != 'run':
            if key_input == 'r':
                cmd_write = 'LED'
                cmt_write = 'LED ON' if self.LED_state else 'LED OFF'
            else:
                cmd_write = 'LED ' + key_input[1:]
                cmt_write = f'LED ON for {key_input[1:]} s'
        elif key_input == 'p':
            cmd_write = f'Pulse {self.pulse_span} {self.pulse_frequency} {self.pulse_width}'
            cmt_write = f'pulsing for {self.pulse_span} s at {self.pulse_frequency} Hz with {self.pulse_width} ms pulse width'
        elif key_input == 't':
            cmd_write = f'LEDandVideo {self.videoLED_timer/1000}'
            cmt_write = f'coordinated video playing and LED with timer = {self.videoLED_timer} ms'
        elif key_input.startswith('set:'):
            key_input = key_input.split(':')[1]
            cmd_write = 'Set_Attribute ' + key_input
            cmt_write = f'set parameter {key_input}'
        elif key_input == 'trig':
            cmd_write = 'Trigger'
            cmt_write = 'send a 100ms trigger signal on the trigger_pin'
        elif key_input.lower().startswith('isi'):
            t_interval = float(key_input[3:])
            cmd_write = f'ISI {t_interval:.3f}'
            cmt_write = f'inter-stimulus interval: {t_interval:.3f} s'
        # Handle pump commands
        elif key_input == 'pump' or key_input.startswith('pump:'):
            cmd_write = key_input
            if key_input == 'pump':
                cmt_write = 'toggle pump state'
            elif key_input == 'pump:on':
                cmt_write = 'turn pump ON'
            elif key_input == 'pump:off':
                cmt_write = 'turn pump OFF'
            else:  # pump:value:XXX
                value = key_input.split(':')[2]
                cmt_write = f'set pump value to {value}/255'
        # Handle shock commands
        elif key_input == 'shock' or key_input.startswith('shock:'):
            cmd_write = key_input
            if key_input == 'shock':
                cmt_write = 'toggle shock pulses'
            elif key_input == 'shock:on':
                cmt_write = 'start shock pulses'
            else:  # shock:off
                cmt_write = 'stop shock pulses'
        # Handle valve commands
        elif key_input == 'air' or key_input.startswith('air:'):
            cmd_write = key_input
            if key_input == 'air':
                cmt_write = 'toggle air valve'
            elif key_input == 'air:on':
                cmt_write = 'open air valve'
            else:  # air:off
                cmt_write = 'close air valve'
        elif key_input == 'odor_a' or key_input.startswith('odor_a:'):
            cmd_write = key_input
            if key_input == 'odor_a':
                cmt_write = 'toggle odor A valve'
            elif key_input == 'odor_a:on':
                cmt_write = 'open odor A valve'
            else:  # odor_a:off
                cmt_write = 'close odor A valve'
        elif key_input == 'odor_b' or key_input.startswith('odor_b:'):
            cmd_write = key_input
            if key_input == 'odor_b':
                cmt_write = 'toggle odor B valve'
            elif key_input == 'odor_b:on':
                cmt_write = 'open odor B valve'
            else:  # odor_b:off
                cmt_write = 'close odor B valve'
        elif key_input == 'stop':
            cmd_write = 'Stop'
            cmt_write = 'send quit command to Arduino to terminate all operations'
        # Handle shortcuts
        elif key_input in self.shortcuts:
            cmd_write = key_input
            cmt_write = f'execute shortcut: {self.shortcuts[key_input]}'
            
        # Only write if we have valid command and comment
        if cmd_write and cmt_write:
            with open(self.protocol_saveas,'a') as f:
                f.write(cmd_write + ' '*(40-len(cmd_write)) + ' # ' + cmt_write + '\n\n')
        
        return 0
    
    def run_protocols(self):
        '''run the protocols in the local protocol folder'''
        if os.path.exists(self.protocol_dir) == False:
            print('Not found the protocol folder. Please create one first.')
            return
        protocol_files = [file for file in os.listdir(self.protocol_dir) if file.endswith('.txt')]
        protocol_files.sort()
        protocol_files = list(reversed(protocol_files))
        if len(protocol_files) == 0:
            print('No protocol file found.')
            return
        print('Available protocols:')
        for i, protocol in enumerate(protocol_files):
            print('\t', f'{i+1:3d}. {protocol}', sep='')
        protocol_input = input('Please input the protocol number (0 to cancel): ')
        if protocol_input.isnumeric():
            protocol_input = int(protocol_input)
            if protocol_input in range(1,len(protocol_files)+1):
                protocol_file = protocol_files[protocol_input-1]
                with open(os.path.join(self.protocol_dir,protocol_file),'r') as f:
                    protocol = f.readlines()
                for line in protocol:
                    line = line[:-1] # remove the '\n' at the end of each line
                    if len(line) > 1 and line[0] != '#':
                        print('\nread command: \033[34m'+line+'\033[0m')
                    line = line.strip()
                    if line.startswith('#'):
                        continue
                    elif line.find('#') > -1:
                        line = line[:line.find('#')].strip()
                    cmd = line.split(' ')
                    cmdlen = len(cmd)
                    self.ClearSerialBuffer()
                    if cmd[0].lower() == 'isi': # inter-stimulus interval
                        self.wait_ISI("ISI" + cmd[1])
                    elif cmd[0].lower() == 'play':
                        if cmdlen == 1:
                            self.deliver_video()
                        else:
                            self.deliver_video_series(int(cmd[1]))
                    elif cmd[0].lower() == 'led':
                        if cmdlen == 1:
                            self.LED_controller()
                        else:
                            self.LED_controller('r'+cmd[1])
                    elif cmd[0].lower() == 'pulse':
                        pulse_backups = [self.update_pulse,self.pulse_span,self.pulse_frequency,self.pulse_width]
                        self.update_pulse = False
                        self.pulse_span = float(cmd[1])
                        self.pulse_frequency = float(cmd[2])
                        self.pulse_width = int(cmd[3])
                        self.LED_pulse_controller()
                        self.update_pulse,self.pulse_span,self.pulse_frequency,self.pulse_width = pulse_backups
                    elif cmd[0].lower() == 'ledandvideo':
                        if cmdlen == 1:
                            self.videoLED_coordination()
                        else:
                            videoLED_backups = [self.videoLED_timer, self.update_timer]
                            self.update_timer = False
                            self.videoLED_timer = int(float(cmd[1])*1000)
                            self.videoLED_coordination()
                            self.videoLED_timer, self.update_timer = videoLED_backups
                    elif cmd[0].lower() == self.stim_name:
                        self.reset_stimulus(stim_new=cmd[1])
                    elif cmd[0].lower() == 'set_attribute':
                        self.update_mutable_attr(''.join(cmd[1:]))
                    elif cmd[0].lower() == 'trigger':
                        self.send_trigger()
                    # Add handling for new commands in protocol parser
                    elif cmd[0].lower() == 'pump':
                        if cmdlen == 1:
                            self.pump_controller('pump')
                        elif cmdlen == 2 and cmd[1] in ['on', 'off']:
                            self.pump_controller(f'pump:{cmd[1]}')
                        elif cmdlen == 3 and cmd[1] == 'value':
                            self.pump_controller(f'pump:value:{cmd[2]}')
                    elif cmd[0].lower() == 'shock':
                        if cmdlen == 1:
                            self.shock_controller('shock')
                        elif cmdlen == 2 and cmd[1] in ['on', 'off']:
                            self.shock_controller(f'shock:{cmd[1]}')
                    elif cmd[0].lower() == 'air':
                        if cmdlen == 1:
                            self.valve_controller('air')
                        elif cmdlen == 2 and cmd[1] in ['on', 'off']:
                            self.valve_controller(f'air:{cmd[1]}')
                    elif cmd[0].lower() == 'odor_a':
                        if cmdlen == 1:
                            self.valve_controller('odor_a')
                        elif cmdlen == 2 and cmd[1] in ['on', 'off']:
                            self.valve_controller(f'odor_a:{cmd[1]}')
                    elif cmd[0].lower() == 'odor_b':
                        if cmdlen == 1:
                            self.valve_controller('odor_b')
                        elif cmdlen == 2 and cmd[1] in ['on', 'off']:
                            self.valve_controller(f'odor_b:{cmd[1]}')
                    elif cmd[0].lower() == 'stop':
                        self.stop_arduino()
                if self.LED_state: # turn off LEDs after protocols if they are on
                    self.LED_controller()
            elif protocol_input == 0:
                print('Loading protocol cancelled.')
                return
            else:
                print('Invalid input.')
                return
        else:
            print('Invalid input, please input a number of the protocol file or 0 to cancel.')
            return
        return 0
    
    def wait_ISI(self, key_input):
        '''wait for the inter-stimulus interval'''
        key_input = key_input[3:]
        if key_input.replace('.','').isnumeric():
            seconds = float(key_input)
            t_start = time.time()
            t_wait = seconds
            t_elapsed = 0
            print_interval = 0.1  # How often to update the display (in seconds)
            last_print_time = t_start
            while t_elapsed < t_wait:
                t_elapsed = time.time()-t_start
                current_time = time.time()
                if current_time - last_print_time >= print_interval:
                    print(f'\rInter-stimulus interval left time: {t_wait-t_elapsed:.1f} s (Press <Ctrl+C>) to interrupt)', end='    ')
                    last_print_time = current_time
            # Print final 0.0 seconds when loop completes
            print(f'\rInter-stimulus interval left time: 0.0 s', end='                                                              ')
            print()
            return 0
        else:
            print('Invalid input. Please input a number.')
            return 1
    
    def show_help(self,key_input='h'):
        '''show help information'''
        help_dict = {
            "h": [
                "show help information",
                "input 'help + command' to show detailed information of the command",
                "e.g. 'help rv' to see the detailed information of 'rv' command",
            ],
            "q":
                "terminate the program",
            
            f"stim or {self.stim_name}" : [
                f"update the {self.stim_name} (stimulus) value",
                f"{self.stim_name} values (names) should match the names of in the loaded videos",
                f"{self.stim_name} value will be asked after input 'stim' or '{self.stim_name}', current available values are: {self.valid_stim}",
            ],
            
            "set": [
                "update currently mutable parameters: ",
                f"{self.mutable_attrs}",
                "e.g. 'set:pulse_span = 5' for updating pulse_span to 5 s",
                "e.g. 'set:videoLED_timer = 5000' for updating videoLED_timer to 5 s, and set update_timer to False",
                f"you can also set the {self.stim_name} value by this method e.g. 'set:stimulus = 40'",
                "Don't forget the colon ':' after 'set'\n",
                "\033[34mparameters (attributes)\033[0m that can be set: ",
                "videoLED_timer: int, unit: ms",
                "LED_retention: int, unit: ms",
                "video_retention: int, unit: ms",
                "well_times: int",
                "u_time: int, unit: s, precision: 0.001 s",
                "update_timer: bool (True/False) or any value that can be converted to bool",
                "update_pulse: bool (True/False) or any value that can be converted to bool",
                "pulse_span: float or int, unit: s, precision: 0.001 s",
                "pulse_frequency: float or int, unit: Hz, precision: 0.001 Hz",
                "pulse_width: int, unit: ms",
                "stimulus: int, should be in the candidate list, unit: ms",
            ],
            
            "show": [
                "show parameters",
                "e.g. 'show:LED_retention' for showing value of LED_retention",
                "Don't forget the colon ':' after 'show'\n",
            ],
            
            "v": [
                "deliver video stimulus",
                "'v' for playing the video once", 
                "'v[number]' for playing the video [number] times, where [number] is an integer",
                "e.g. 'v5' for playing the video 5 times",
            ],
            
            "r": [
                "switch on/off red LED, an LED timer can be set by 'r[number]'",
                "e.g. 'r' for switching on/off the LED",
                "e.g. 'r5' for 5 seconds; 'r2.5' for 2.5 seconds",
            ],
            
            "t": [
                "deliver video stimulus after/before a LED timer, the timer time well be asked after pressing 't'",
                "e.g. later input 5 for video playing being set to 5 s after LED; -2.5 for LED being set to 2.5 s after video playing",
                "e.g. 0 means video playing and LED are delivered simultaneously",
                "you can use 'set:update_timer = False (0)' to disable the timer update, and 'set:update_timer = True (1)' to enable it",
                "when set:update_timer = False, the timer will not be updated, and the timer time will be fixed to the last given value",
                "but you can always change the timer time by input 'update:videoLED_timer = number' whose unit is ms",
            ],
            
            "p": [
                "deliver LED pulses",
                "if the update_pulse attribute is set to False, the pulse parameters will be the last given values",
                "the update_pulse is default to True, and you can change it by 'set:update_pulse = False' or 'set:update_pulse = True'",
                "when update_pulse is set to True, the following parameters will be asked after pressing 'p':",
                "pulse_span: the total time of the pulse train, unit: s (float, precision: 0.001 s)",
                "pulse_frequency: the frequency of the pulse train, unit: Hz (float, precision: 0.001 Hz)",
                "pulse_width: the width of the pulse, unit: ms (int)",
                "alternatively, you can use 'set:pulse_span = number' in sec to set the pulse_span, and so on, even when update_pulse = False",
            ],
            
            "load": [
                "run available local protocol files",
                "the protocol file is on-the-fly updated, which allows you to call 'load' command to repeat previous stimuli in a running sessions",
            ],
            
            "well": [
                "well 会被说出来",
                "you can modify the well times by 'set:well_times = [number]', when well_times = 0, surprize!!!",
            ],
            
            "u":
                "magic will happen",
            
            "run":
                "to run or not to run, that is the question.",
            
            "trig": 
                "send a 10-ms trigger signal on the trigger_pin of the Arduino",
            
            "isi": [
                "wait for the Inter-Stimulus Interval(ISI) in seconds",
                "e.g. 'isi5' for 5 seconds",
                "e.g. 'isi2.5' for 2.5 seconds",
                "\033[33mThe exact duration of an 'isi' will be automatically adjusted to compensate for the overhead of the command execution and hardware communication.\033[0m",
                
            ],
            
            "pump": [
                "control the air pump",
                "usage: 'pump' to toggle pump on/off",
                "usage: 'pump:on' to turn on the pump",
                "usage: 'pump:off' to turn off the pump",
                "usage: 'pump:value:XXX' to set pump power value (0-255)",
                "e.g., 'pump:value:200' sets the pump to 200/255 power"
            ],
            
            "shock": [
                "control the shock pulses (0.2 Hz, 1.25s pulse width)",
                "usage: 'shock' to toggle shock pulses on/off",
                "usage: 'shock:on' to start shock pulses",
                "usage: 'shock:off' to stop shock pulses"
            ],
            
            "air": [
                "control the air valve",
                "usage: 'air' to toggle air valve open/closed",
                "usage: 'air:on' to open the air valve",
                "usage: 'air:off' to close the air valve",
                "Note: Pump must be on to open valves"
            ],
            
            "odor_a": [
                "control the odor A valve",
                "usage: 'odor_a' to toggle odor A valve open/closed",
                "usage: 'odor_a:on' to open odor A valve",
                "usage: 'odor_a:off' to close odor A valve",
                "Note: Pump must be on to open valves"
            ],
            
            "odor_b": [
                "control the odor B valve",
                "usage: 'odor_b' to toggle odor B valve open/closed",
                "usage: 'odor_b:on' to open odor B valve",
                "usage: 'odor_b:off' to close odor B valve",
                "Note: Pump must be on to open valves"
            ],
            
            "stop": [
                "send 'quit' command to Arduino to terminate all ongoing operations",
                "resets all state tracking variables for Arduino operations", 
                "use this if Arduino seems to be in an inconsistent state"
            ],
            
            "\033[33mcombined commands\033[0m": [
                "You can combine multiple commands with '>'",
                "e.g. r5>isi5>set:pulse_span=10>p",
                "e.g. r5 > isi5 > set:pulse_span = 10 > p > stim > v",
                "You can also use repetition patterns with parentheses and '*'",
                "e.g. (p>isi2)*5 to repeat the sequence 'p>isi2' five times",
                "e.g. trig > isi120 > (p > isi4) * 10 > r2",
                "Please note that the '*' operator should be used with parentheses and located \033[34mafter\033[0m the ')' operator",
            ],
            
            "shortcuts": [
                "manage command shortcuts",
                "usage: input 'shortcuts' to list all available shortcuts",
                "usage: use '<-' to make new shortcuts", 
                "usage: '`shortcut_name` <- `command 1` > `command 2`' to save a new shortcut",
                "usage: input the name to use a shortcut",
                "example: 'test_odor <- pump:on > odor_a:on > isi5 > odor_a:off > pump:off'",
                "example: then input 'test_odor' to execute the above shortcut",
                "shortcuts are saved in the command_shortcuts.txt file"
            ],
            
            "<Ctrl+C>": [
                "Press <Ctrl+C> to stop the current command and terminate the Arduino execution",
                "This will not stop the program, but lead to a new prompt to determine the next action.",
                "You can then choose to continue or terminate the program",
            ],
            
            "\033[33mAdditional Info\033[0m": [
                "the current protocol will be automatically saved to the protocol folder, except for the 'load' command",
                "you can always press <Ctrl+C> or delete the progress to stop the program",
                "if PemissionError raised when communicate with Arduino, please restart the program and simply try again",
            ],
        }
        
        curr_key = key_input.lower()
        if curr_key == 'h' or curr_key == 'help':
            print('\nHelp information: input \033[34mkeys\033[0m and their functions')
            for key in help_dict:
                notes = help_dict[key]
                if isinstance(notes, list):
                    print('\033[34m'+key+'\033[0m','--')
                    for note in notes:
                        print('\t',note)
                else:
                    print('\033[34m'+key+'\033[0m','--\n\t',notes)
                print()
        elif curr_key.split(' ')[0] == 'help' and curr_key.split(' ')[1] in help_dict:
            k0 = curr_key.split(' ')[1]
            if isinstance(help_dict[k0], list):
                print('\033[34m'+k0+'\033[0m','--')
                for note in help_dict[k0]:
                    print('\t',note)
            else:
                print('\033[34m'+k0+'\033[0m','--\n\t',help_dict[k0])
        else:
            print('Invalid input or unknown command.')
            return
        return 0
    
    
    def start_journey(self):
        '''start the interactive user interface, journey to the fantastic world'''
        print('\nWelcome to the stimulation world!\n')
        print('Enter "h" or "help" to show all available operations')
        print('You can combine multiple commands with ">" character.')
        print('For example: "r5>isi5>set:pulse_span=10>p"\n')
        print('You can also use repetition patterns like: "(p>isi2)*5" or "trig>(r2>isi5)*3>p", where "*" should be \033[34mafter\033[0m ")" operator\n')
        
        if not self.shut_backgroud:
            self.window_video = playstim.initialize_window(self.frms[0])
        print(f'{self.stim_name} = {self.stimulus}')
        
        while True:
            try:
                execute_state = None
                key_input = input(self.prompt)
                self.ClearSerialBuffer()
                
                # Log the original input command with a timestamp
                if self.log_file:
                    with open(self.log_file, 'a') as log:
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        log.write(f"[{timestamp}] Input: {key_input}\n")
                
                # Check for shortcut creation syntax
                if '<-' in key_input:
                    parts = key_input.split('<-', 1)
                    shortcut_name = parts[0].strip()
                    command_series = parts[1].strip()
                    self.save_shortcut(shortcut_name, command_series)
                    continue
                
                # Check if this is a wrapped command series with repetition
                if '(' in key_input and '*' in key_input:
                    self.parse_wrapped_commands(key_input)
                    continue
                
                # Check if this is a regular combined command series
                elif '>' in key_input:
                    self.parse_combined_commands(key_input)
                    continue
                
                # Validate single command
                validated_cmd = self.validify_command(key_input)
                if validated_cmd is None and key_input:  # Only show error for non-empty input
                    print('Invalid command! Please input a valid command or "h" for help.')
                    continue
                    
                # Original command processing
                if key_input == 'q': # quit
                    execute_state = self.stop_arduino()
                    break
                elif key_input == '':
                    print('No valid input detected, please input a command or "h" for help.')
                    continue
                elif key_input == 'h' or key_input.startswith('help'): # show the help information
                    self.show_help(key_input)
                elif key_input == 'shortcuts':  # list all shortcuts
                    self.list_shortcuts()
                elif key_input in self.shortcuts:  # execute shortcut
                    execute_state = self.execute_shortcut(key_input)
                elif key_input.startswith('v'):  # Unified video command
                    execute_state = self.deliver_video_command(key_input)
                elif key_input == 'stim' or key_input == self.stim_name: # reset stimulus value from self.valid_stim
                    execute_state = self.reset_stimulus()
                elif key_input[0] == 'r' and key_input != 'run': # switch ON/OFF the red LEDs
                    execute_state = self.LED_controller(key_input)
                elif key_input == 'p': # LED pulsing
                    execute_state = self.LED_pulse_controller()
                elif key_input == 't': # timer for coordinating the LED and video playing
                    execute_state = self.videoLED_coordination()
                elif key_input == 'well': # 说well的时候，well会被说出来
                    self.say_well()
                elif key_input == 'u': # 说u的时候，u会被yz说出来
                    self.say_u()
                elif key_input == 'run': # "when I say run, RUN!"
                    print('The game is on!')
                elif key_input == 'load': # load existed protocols
                    self.run_protocols()
                elif key_input.startswith('set:'): # update the parameters of video playing, e.g. self.stimulus = 40, or show the attributes, e.g. self.stimulus
                    execute_state = self.update_mutable_attr(key_input)
                elif key_input.startswith('show:'):
                    self.show_attr(key_input)
                elif key_input == 'trig':  # send trigger signal
                    execute_state = self.send_trigger()
                elif key_input.lower().startswith('isi'):
                    execute_state = self.wait_ISI(key_input)
                # Add new command handling for pump, shock, and valves
                elif key_input == 'pump' or key_input.startswith('pump:'):
                    execute_state = self.pump_controller(key_input)
                elif key_input == 'shock' or key_input.startswith('shock:'):
                    execute_state = self.shock_controller(key_input)
                elif key_input == 'air' or key_input.startswith('air:'):
                    execute_state = self.valve_controller(key_input)
                elif key_input == 'odor_a' or key_input.startswith('odor_a:'):
                    execute_state = self.valve_controller(key_input)
                elif key_input == 'odor_b' or key_input.startswith('odor_b:'):
                    execute_state = self.valve_controller(key_input)
                elif key_input == 'stop':
                    execute_state = self.stop_arduino()
                else:
                    print('Invalid input! Please input a valid command.')
                    
                if execute_state == 0:
                    self.write_protocols(key_input)
            except KeyboardInterrupt:
                print('\n\033[33mKeyboard Interrupt detected!\033[0m')
                self.stop_arduino()
                go_on = input('\033[33mDo you want to Continue(Y) or Terminate(n) the program? (Y/n): \033[0m')
                if go_on.lower() == 'y':
                    print('Continuing the program...')
                    continue
                else:
                    break
        self.terminate()
    
    def send_trigger(self):
        """Send a trigger signal to the Arduino to activate the trigger_pin for 100ms"""
        if self.ser == '':
            print('\nSerial communication is unavailable. Trigger cannot be sent.\n')
            return
        
        t_timeout = 5  # timeout in seconds
        self.ser.write(b'trigger\n')
        t_trigger = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print('Sending trigger signal...')
        
        # Wait for feedback from Arduino
        t_arduino = time.time()
        while True:
            t_wait = time.time() - t_arduino
            if t_wait > t_timeout:
                raise TimeoutError('Arduino timeout')
            if self.ser.inWaiting() > 0:
                fb = self.ser.readline().decode()[:-1]
                if fb == 'Trigger ON':
                    t_trigger_on = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    # print(fb)
                elif fb == 'Trigger OFF':
                    t_trigger_off = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    # print(fb)
                    print('Trigger signal sent successfully.')
                    break
                else:
                    raise ValueError(f'Wrong feedback from Arduino: {fb}')
        
        # Log the trigger event
        with open(self.log_file, 'a') as log:
            log.write('Trigger sent at {}\n'.format(t_trigger))
            log.write('Feedback Trigger ON at {}\n'.format(t_trigger_on))
            log.write('Feedback Trigger OFF at {}\n'.format(t_trigger_off))
            log.write('\n')
        
        return 0
    
    def parse_combined_commands(self, cmd_series):
        """Parse and execute a series of commands separated by '>' characters"""
        commands = cmd_series.split('>')
        validated_commands = []
        
        # Hardware communication delay constant (seconds)
        HARDWARE_DELAY = 0.03  # Estimated average delay per hardware command
        
        # First, validate all commands in the series
        for i, cmd in enumerate(commands):
            cmd = cmd.strip()
            validated_cmd = self.validify_command(cmd)
            
            if validated_cmd is None:
                print(f"\nInvalid command found in series: \033[31m{cmd}\033[0m")
                print("Command series execution cancelled.")
                return 1
                
            validated_commands.append(validated_cmd)
        
        # Calculate timing information and prepare adjusted commands
        adjusted_commands = []
        total_command_time = 0
        isi_indices = []
        isi_durations = []
        
        # First pass - calculate timing for each command and store expected durations
        expected_durations = {}  # Dictionary to store expected duration for each command
        
        for i, cmd in enumerate(validated_commands):
            if cmd.startswith('r') and cmd != 'run' and len(cmd) > 1:
                # LED command with duration (e.g., 'r5')
                try:
                    duration = float(cmd[1:])
                    total_command_time += duration
                    expected_durations[i] = duration
                except ValueError:
                    total_command_time += HARDWARE_DELAY
                    expected_durations[i] = HARDWARE_DELAY
            elif cmd == 'p':
                # Pulse command uses pulse_span
                total_command_time += self.pulse_span
                expected_durations[i] = self.pulse_span
            elif cmd.startswith('isi'):
                # Record ISI commands for later adjustment
                try:
                    duration = float(cmd[3:])
                    isi_indices.append(i)
                    isi_durations.append(duration)
                    total_command_time += duration
                    expected_durations[i] = duration
                except ValueError:
                    total_command_time += HARDWARE_DELAY
                    expected_durations[i] = HARDWARE_DELAY
            else:
                # Other commands
                total_command_time += 0
                expected_durations[i] = 0
        
        # Calculate total hardware overhead time - excluding ISI commands which don't require hardware communication
        # Calculate total hardware overhead - only count commands after the last ISI
        if isi_indices:
            # Find the index of the last ISI command
            last_isi_index = max(isi_indices)
            # Count commands after the last ISI
            commands_after_last_isi = len(validated_commands) - last_isi_index - 1
            residue_hardware_overhead = commands_after_last_isi * HARDWARE_DELAY
        else:
            # If no ISI commands exist, count all commands
            residue_hardware_overhead = len(validated_commands) * HARDWARE_DELAY
        
        # Copy commands without pre-adjusting ISI durations
        adjusted_commands = validated_commands.copy()
        
        # Just print timing information for ISI commands
        if isi_indices:
            print(f"Estimated total time: {total_command_time + residue_hardware_overhead:.3f}s (including ~{residue_hardware_overhead:.3f}s hardware overhead)")
            print(f"Found {len(isi_indices)} ISI commands that will be dynamically adjusted during execution")
            
        # Now execute the validated commands
        print(f"Executing command series: {' > '.join(validated_commands)}")
        results = []
        
        # Track timing for dynamic ISI adjustments
        execution_start = time.time()
        accumulated_drift = 0  # Running total of time differences between expected and actual execution
        command_start_times = {}  # To track when each command starts
        
        # Record the start time once for the whole series
        self.t_last_stim = time.time()
        
        for i, cmd in enumerate(adjusted_commands):
            # Record command start time
            command_start_times[i] = time.time()
            
            print(f"\nExecuting command {i+1}/{len(adjusted_commands)}: \033[34m{cmd}\033[0m")
            
            # Process the command, if it's an ISI command, dynamically adjust it
            if cmd.startswith('isi') and i > 0:
                # Get the original duration
                original_duration = float(cmd[3:])
                
                # Calculate adjustment based on accumulated drift
                # If accumulated_drift is positive, we're ahead of schedule, so increase ISI
                # If accumulated_drift is negative, we're behind schedule, so decrease ISI
                adjusted_duration = max(0.1, original_duration + accumulated_drift)
                
                if abs(accumulated_drift) > 0.01:  # Only report if drift is significant
                    drift_direction = "ahead of" if accumulated_drift > 0 else "behind"
                    print(f"Timing drift: {abs(accumulated_drift):.3f}s {drift_direction} schedule")
                    print(f"Adjusting ISI from {original_duration:.3f}s to {adjusted_duration:.3f}s")
                
                # Create a new ISI command with adjusted time
                adjusted_isi = f"isi{adjusted_duration:.3f}"
                result = self.process_command(adjusted_isi)
            else:
                result = self.process_command(cmd)
                
            results.append(result)
            
            # Call write_protocols with original command for logging purposes
            if result == 0:
                original_cmd = validated_commands[i]
                self.write_protocols(original_cmd, skip_isi=True)
            
            # Calculate actual time taken for this command
            command_end_time = time.time()
            actual_duration = command_end_time - command_start_times[i]
            
            # Update our accumulated drift calculation
            if i in expected_durations:
                expected = expected_durations[i]
                command_drift = expected - actual_duration
                accumulated_drift += command_drift  # Positive means ahead of schedule
                
                if abs(command_drift) > 0.01 and not cmd.startswith('isi'):
                    print(f"Command timing: ideal {expected:.3f}s, actual {actual_duration:.3f}s, drift {command_drift:.3f}s")
            
            # Stop execution if a command returns non-zero (error)
            if result != 0:
                print(f"Command series stopped at command {i+1}: '{cmd}'")
                break
        
        # Report actual execution time and timing accuracy
        execution_time = time.time() - execution_start
        estimated_total = sum(expected_durations.values()) + residue_hardware_overhead
        
        if execution_time > 1: # if execution time is more than 1 second, print the time
            print(f"\nCommand series completed in {execution_time:.3f} seconds")
            print(f"Expected duration: {estimated_total:.3f} seconds")
            if abs(execution_time - estimated_total) > 0.03:
                accuracy = abs(execution_time - estimated_total)
                print(f"Timing accuracy: {accuracy:.2f}% ({'slower' if execution_time > estimated_total else 'faster'} than expected)")
            else:
                print("Timing accuracy: Excellent (within 30 ms)")
        
        return 0 if all(r == 0 for r in results) else 1

    def process_command(self, command):
        """Process a single command and return execution status"""
        # Check if command is a shortcut
        if command in self.shortcuts:
            return self.execute_shortcut(command)
            
        if command == '':
            return self.deliver_video()
        elif command == 'shortcuts':
            return self.list_shortcuts()
        elif command.startswith('v'):  # Unified video command
            return self.deliver_video_command(command)
        elif command == 'stim' or command == self.stim_name:
            return self.reset_stimulus()
        elif command[0] == 'r' and command != 'run':
            return self.LED_controller(command)
        elif command == 'p':
            return self.LED_pulse_controller()
        elif command == 't':
            return self.videoLED_coordination()
        elif command.startswith('set:'):
            return self.update_mutable_attr(command)
        elif command.startswith('show:'):
            return self.show_attr(command) or 0  # Ensure it returns 0 for success
        elif command == 'trig':
            return self.send_trigger()
        elif command.lower().startswith('isi'):
            return self.wait_ISI(command)
        # Add new command handlers
        elif command == 'pump' or command.startswith('pump:'):
            return self.pump_controller(command)
        elif command == 'shock' or command.startswith('shock:'):
            return self.shock_controller(command)
        elif command == 'air' or command.startswith('air:'):
            return self.valve_controller(command)
        elif command == 'odor_a' or command.startswith('odor_a:'):
            return self.valve_controller(command)
        elif command == 'odor_b' or command.startswith('odor_b:'):
            return self.valve_controller(command)
        elif command == 'stop':
            return self.stop_arduino()
        # Existing commands
        elif command == 'h' or command.startswith('help'):
            return self.show_help(command)
        elif command == 'well':
            return self.say_well()
        elif command == 'u':
            return self.say_u()
        elif command == 'run':
            print('The game is on!')
            return 0
        elif command == 'load':
            return self.run_protocols()
        elif command == 'q':
            return -1  # Special return value for quit
        else:
            print(f"Unknown command: '{command}'")
            return 1

    def validify_command(self, command):
        """
        Validate and normalize a command string.
        
        Parameters:
            command (str): The command to validate
                
        Returns:
            str: The validated/normalized command if valid
            None: If the command is invalid
        """
        if not command or not isinstance(command, str):
            return None
    
        # Check if command is a shortcut
        if command in self.shortcuts:
            return command
    
        # Normalize command by trimming whitespace
        command = command.strip()
    
        # Empty command is valid (play video)
        if not command:
            return ''
    
        # Simple command validation
        if command == 'q' or command == 'h' or command == 'v' or command == 'p' or \
           command == 't' or command == 'well' or command == 'u' or command == 'run' or \
           command == 'load' or command == 'trig' or command == self.stim_name or \
           command == 'stim' or command.startswith('help') or \
           command == 'pump' or command == 'shock' or command == 'air' or \
           command == 'odor_a' or command == 'odor_b' or command == 'stop' or \
           command == 'shortcuts':
            return command
    
        # Commands with parameters
        if command.startswith('v'):
            # Validate v[number] commands
            if len(command) > 1 and command[1:].isnumeric():
                return command
            elif command == 'v':
                return command
        elif command[0] == 'r' and command != 'run':
            # Validate r commands (LED control)
            if len(command) == 1:
                return 'r'
            elif command[1:].replace('.', '').isnumeric():
                return command
        elif command.startswith('set:'):
            # Validate set commands
            parts = command.split(':')
            if len(parts) != 2 or not parts[1].strip():
                return None
            attr_val = parts[1].strip().replace(' ', '')
            if '=' not in attr_val:
                return None
            attr, val = attr_val.split('=')
            if not hasattr(self, attr) or attr not in self.mutable_attrs:
                return None
            return command
        elif command.startswith('show:'):
            # Validate show commands
            parts = command.split(':')
            if len(parts) != 2 or not parts[1].strip():
                return None
            attr = parts[1].strip()
            if not hasattr(self, attr):
                return None
            return command
        elif command.lower().startswith('isi'):
            # Validate ISI commands
            if len(command) <= 3:
                return None
            if not command[3:].replace('.', '').isnumeric():
                return None
            return command
        # New command validations
        elif command.startswith('pump:'):
            if command in ['pump:on', 'pump:off'] or command.startswith('pump:value:'):
                if command.startswith('pump:value:'):
                    value_str = command[11:]
                    if not value_str.isnumeric() or not (0 <= int(value_str) <= 255):
                        return None
                return command
        elif command.startswith('shock:'):
            if command in ['shock:on', 'shock:off']:
                return command
        elif command.startswith('air:'):
            if command in ['air:on', 'air:off']:
                return command
        elif command.startswith('odor_a:'):
            if command in ['odor_a:on', 'odor_a:off']:
                return command
        elif command.startswith('odor_b:'):
            if command in ['odor_b:on', 'odor_b:off']:
                return command
    
        # If we get here, the command is not recognized
        return None

    def pump_controller(self, key_input='pump'):
        '''Control the pump: turn on/off or set value'''
        result = 0
        
        if key_input == 'pump':  # Toggle pump state
            self.pump_state = playstim.pump_switch(self.pump_state, self.ser, self.log_file)
        elif key_input == 'pump:on':  # Turn on pump
            self.pump_state = playstim.pump_switch(self.pump_state, self.ser, self.log_file, turn_on=True)
        elif key_input == 'pump:off':  # Turn off pump
            self.pump_state = playstim.pump_switch(self.pump_state, self.ser, self.log_file, turn_on=False)
        elif key_input.startswith('pump:value:'):  # Set pump value
            value_str = key_input[11:]
            if value_str.isnumeric():
                value = int(value_str)
                if 0 <= value <= 255:
                    result = playstim.set_pump_value(self.ser, self.log_file, value)
                    if result == 0:
                        self.pump_value = value
                else:
                    print('\033[31mInvalid pump value. Must be an integer between 0-255\033[0m')
                    return 1
            else:
                print('\033[31mInvalid pump value. Must be an integer between 0-255\033[0m')
                return 1
        else:
            print('Invalid pump command')
            return 1
        
        return result

    def shock_controller(self, key_input='shock'):
        '''Control shock pulses: turn on/off'''
        if key_input == 'shock':  # Toggle shock state
            self.shock_state = playstim.shock_switch(self.shock_state, self.ser, self.log_file)
            return 0
        elif key_input == 'shock:on':  # Turn on shock
            self.shock_state = playstim.shock_switch(self.shock_state, self.ser, self.log_file, turn_on=True)
            return 0
        elif key_input == 'shock:off':  # Turn off shock
            self.shock_state = playstim.shock_switch(self.shock_state, self.ser, self.log_file, turn_on=False)
            return 0
        else:
            print('Invalid shock command')
            return 1

    def valve_controller(self, key_input):
        '''Control air/odor valves: turn on/off'''
        valve_name = key_input.split(':')[0] if ':' in key_input else key_input
        self.last_valve_attempted = valve_name  # Track the last valve for error handling
        
        if valve_name in ['air', 'odor_a', 'odor_b'] and ':on' in key_input and not self.pump_state:
            print('\033[33mWarning: Cannot open valve - Pump is OFF\033[0m')
            return 1
        
        if valve_name == 'air':
            self.air_state = self.toggle_valve('air', self.air_state, key_input)
        elif valve_name == 'odor_a':
            self.odor_a_state = self.toggle_valve('odor_a', self.odor_a_state, key_input)
        elif valve_name == 'odor_b':
            self.odor_b_state = self.toggle_valve('odor_b', self.odor_b_state, key_input)
        else:
            print('Invalid valve command')
            return 1
        return 0

    def toggle_valve(self, valve_name, current_state, key_input):
        '''Helper function to toggle or set valve state'''
        if key_input == f'{valve_name}':
            return playstim.valve_switch(valve_name, current_state, self.ser, self.log_file)
        elif key_input == f'{valve_name}:on':
            return playstim.valve_switch(valve_name, current_state, self.ser, self.log_file, turn_on=True)
        elif key_input == f'{valve_name}:off':
            return playstim.valve_switch(valve_name, current_state, self.ser, self.log_file, turn_on=False)
        return current_state

    def stop_arduino(self):
        """Send quit command to Arduino to terminate all operations"""
        if self.ser == '':
            print('\nSerial communication is unavailable. Cannot send quit command.\n')
            return 1
        
        result = playstim.quit_all_operations(self.ser, self.log_file)
        
        # Reset all state tracking variables related to Arduino operations
        self.LED_state = 0
        self.pump_state = False
        self.shock_state = False
        self.air_state = False
        self.odor_a_state = False
        self.odor_b_state = False
        
        return result

    def list_shortcuts(self):
        """List all available shortcuts"""
        # Reload shortcuts from file to ensure latest changes are reflected
        self.load_shortcuts()
        
        if not self.shortcuts:
            print("No shortcuts available. Use '<shortcut_name> <- <command> > <command>' to create a shortcut")
            return
            
        print("\nAvailable shortcuts:")
        for name, cmd_series in self.shortcuts.items():
            print(f"  \033[34m{name}\033[0m: {cmd_series}")
        print("\nUse a shortcut by typing its name")
        return 0