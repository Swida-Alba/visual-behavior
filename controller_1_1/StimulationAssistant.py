import os
import cv2
import time
import numpy as np
import LoomingFunc as playstim
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class VideoDelivery:
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
    }

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
            self.ser = playstim.SetUpSerialPort(board_type=self.board_type)
        self.LED_state = 0
        
        # building the save path of log files
        if not self.save_path:
            self.save_path = os.path.abspath(os.path.join(self.script_path, '..', 'Jail', self.t_today))
        if not os.path.exists(self.save_path): os.mkdir(self.save_path)
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
            self.log_name = input('\033[33mPlease input the custom file name or press <Enter> directly: \033[0m')
            if self.log_name:
                self.log_name = self.t_today + '_' + self.log_name + '_log.txt'
            else:
                self.log_name = self.t_today + '_log.txt'
        print(f'Log file will be saved as: {self.log_name}')
        
        self.log_file = os.path.join(self.save_path, self.log_name)
    
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
        cv2.destroyAllWindows()
        if self.ser: self.ser.close()
        print('Sessions terminated.')
        if os.path.exists(self.protocol_saveas): print(f'Current protocol was saved as: {self.protocol_saveas}')
        return 0
    
    def deliver_video(self):
        print(f'{self.stim_name} = {self.stimulus}')
        real_fps, interval, t_play, t_end = playstim.play_video(self.frms, self.read_fps, self.window_video, retention_time=self.video_retention)
        playstim.write_video_log(self.log_file, real_fps, self.read_fps, self.stimulus, t_play, t_end, self.LED_state, duration = np.sum(interval)/1000)
        self.window_video = playstim.initialize_window(self.frms[0])
        return 0
    
    def deliver_video_series(self, loop_times = None):
        if loop_times is not None:
            self.play_times = loop_times
            for i in range(self.play_times):
                self.deliver_video()
        else:
            loop_input = input(f'Please input the loop times ({self.stim_name} = {self.stimulus} ms): ')
            if loop_input.isnumeric():
                self.play_times = int(loop_input)
                print(f'stimulus series: {self.play_times} times')
                with open(self.log_file,'a') as log:
                    log.write(f'stimulus series: {self.play_times} times\n')
                    log.write('\n')
                for i in range(self.play_times):
                    self.deliver_video()
            else:
                print('Invalid input, please input an integer.')
                return
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
            print('Invalid input. <r> should be followed by a number to specify the LED ON time (s).')
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
                if int(pw_input) < 5:
                    pw_input = 5
                    print('\033[33mPulse width is set to 5 ms.\033[0m')
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
    
    def ClearSerialBuffer(self, print_flag = False):
        '''check and clear the serial buffer'''
        if not self.ser:
            return
        else:
            lineNum = 0
            while self.ser.inWaiting() > 0:
                fb = self.ser.readline().decode()[:-1]
                lineNum += 1
                print(f'\033[30mCleared serial buffer -- line {lineNum}: {fb}\033[0m')
            if lineNum == 0 and print_flag:
                print('No info in serial buffer.')
            return 0
    
    def write_protocols(self,key_input):
        '''write current command to local protocol file'''
        if hasattr(self,'t_last_stim'):
            self.t_stim_end = time.time()
            t_interval = self.t_stim_end - self.t_last_stim
            self.t_last_stim = self.t_stim_end
            cmd_write = f'ISI {t_interval:.3f}'
            cmt_write = f'inter-stimulus interval: {t_interval:.3f} s'
            with open(self.protocol_saveas,'a') as f:
                f.write(cmd_write + ' '*(40-len(cmd_write)) + ' # ' + cmt_write + '\n\n')
        else:
            self.t_last_stim = time.time()
        if key_input == '':
            cmd_write = 'Play' # command to write
            cmt_write = 'playing video stimulus' # comment to write
        elif key_input == 'v':
            cmd_write = 'Play ' + str(self.play_times)
            cmt_write = 'playing video for ' + str(self.play_times) + ' times'
        elif key_input == 'stim' or key_input == self.stim_name:
            cmd_write = f'{self.stim_name} ' + str(self.stimulus)
            cmt_write = f'set {self.stim_name} to {self.stimulus}'
        elif key_input[0] == 'r':
            if key_input == 'r':
                cmd_write = 'LED'
                if self.LED_state:
                    cmt_write = 'LED ON'
                else:
                    cmt_write = 'LED OFF'
            else:
                cmd_write = 'LED ' + key_input[1:]
                cmt_write = f'LED ON for {key_input[1:]} s'
        elif key_input == 'p':
            cmd_write = 'Pulse ' + str(self.pulse_span) + ' ' + str(self.pulse_frequency) + ' ' + str(self.pulse_width)
            cmt_write = f'pulsing for {self.pulse_span} s at {self.pulse_frequency} Hz with {self.pulse_width} ms pulse width'
        elif key_input == 't':
            cmd_write = 'LEDandVideo ' + str((self.videoLED_timer)/1000)
            cmt_write = f'coordinated video playing and LED with timer = {self.videoLED_timer} ms'
        elif key_input.startswith('set:'):
            key_input = key_input.split(':')[1]
            cmd_write = 'Set_Attribute ' + key_input
            cmt_write = f'set parameter {key_input}'
        with open(self.protocol_saveas,'a') as f:
            f.write(cmd_write + ' '*(40-len(cmd_write)) + ' # ' + cmt_write + '\n\n')
        return 0
    
    def run_protocols(self):
        '''run the protocols in the local protocol folder'''
        if os.path.exists(self.protocol_dir) == False:
            print('Not found the protocol folder. Please create one first.')
            return
        protocol_files = [file for file in os.listdir(self.protocol_dir) if file.endswith('.txt')]
        protocol_files = list(reversed(protocol_files))
        if len(protocol_files) == 0:
            print('No protocol file found.')
            return
        print('Available protocols:')
        for i, protocol in enumerate(protocol_files):
            print('\t', f'{i+1:3d}. {protocol}', sep='')
        protocol_input = input('Please input the protocol number: ')
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
                        t_start = time.time()
                        t_wait = float(cmd[1])
                        t_elapsed = 0
                        while t_elapsed < t_wait:
                            t_elapsed = time.time()-t_start
                            print(f'\rISI left time: {t_wait-t_elapsed:.2f} s', end='    ')
                        print()
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
                if self.LED_state: # turn off LEDs after protocols if they are on
                    self.LED_controller()
            else:
                print('Invalid input.')
                return
        else:
            print('Invalid input.')
            return
        return 0
    
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
            
            "<Enter>": 
                "Press <Enter> key directly to deliver video stimulus",
            
            "v": 
                "deliver video stimulus for multiple times, times will be asked after entering 'v' mode",
            
            "r": [
                "switch on/off red LED, an LED timer can be set by 'r'+number",
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
                "if the update_pulse attribute is set to False, the pulse parameters will not be updated, and the pulse parameters will be fixed to the last given values",
                "the update_pulse is default to True, and you can change it by the commands, 'set:update_pulse = False (0)' or 'set:update_pulse = True (1)'",
                "when update_pulse is set to True, the following parameters will be asked after pressing 'p':",
                "pulse_span: the total time of the pulse train, unit: s (float, precision: 0.001 s)",
                "pulse_frequency: the frequency of the pulse train, unit: Hz (float, precision: 0.001 Hz)",
                "pulse_width: the width of the pulse, unit: ms (int)",
                "alternatively, you can use 'set:pulse_span = number (s)' to set the pulse_span, and so on",
            ],
            
            "load": [
                "run available local protocol files",
                "the protocol file is real-time updated, which means you can call 'load' command to repeat previous stimuli even in the currently running sessions",
            ],
            
            "well":
                "you can modify the well times by 'set:well_times = number', when well_times = 0, surprize!!!",
            
            "u":
                "magic will happen",
            
            "run":
                "???",
            
            "\033[33mNotes (this is not a command, just notes)\033[0m": [
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
        while True:
            execute_state = None
            key_input = input(self.prompt)
            self.ClearSerialBuffer()
            if key_input == 'q': # quit
                break
            elif key_input == 'h' or key_input.startswith('help'): # show the help information
                self.show_help(key_input)
            elif key_input == '': # play video
                execute_state = self.deliver_video()
            elif key_input == 'v': # play video series
                execute_state = self.deliver_video_series()
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
            else:
                print('Invalid input! Please input a valid command.')
            if execute_state == 0:
                self.write_protocols(key_input)
        self.terminate()
        