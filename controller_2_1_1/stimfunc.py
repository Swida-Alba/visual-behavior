import os
import cv2
import time
import serial
import shutil
import platform
import serial.tools.list_ports
import matplotlib.pyplot as plt
import moviepy.editor # requires moviepy==1.0.3
# Magic happends here, but I quit figuring out why. The moviepy.editor improves the performance of the video playing dramatically.
import numpy as np
from datetime import datetime, timedelta
from types import SimpleNamespace
from matplotlib.patches import Ellipse

def get_existed_files(folder, prefix = '', suffix = '', containing = ''):
        files = []
        for file in os.listdir(folder):
            if file.startswith(prefix) and file.endswith(suffix) and containing in file:
                files.append(file)
        return files

def read_video(video_dir):
    cap = cv2.VideoCapture(video_dir)
    read_fps= int(cap.get(cv2.CAP_PROP_FPS)) # frame rate
    frame_list = []
    while(cap.isOpened()):
        ret, frame = cap.read()
        if ret == False:
            break
        frame_list.append(frame)
    cap.release()
    return frame_list, read_fps

def initialize_window(img_to_show=None,window='image',window_size=None,window_pos=(1920,0),full_screen=True,always_on_top=False):
    if img_to_show is None:
        img_to_show = np.full((500,500,3),255,dtype=np.uint8)
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    # defaultly move the window to the second monitor, please make sure the second monitor is on the right of the first monitor
    cv2.moveWindow(window, *window_pos) 
    if full_screen: 
        cv2.setWindowProperty(window,cv2.WND_PROP_FULLSCREEN,cv2.WINDOW_FULLSCREEN) # set the image to full screen
    elif window_size is not None: 
        cv2.resizeWindow(window, *window_size)
    if always_on_top:
        cv2.setWindowProperty(window, cv2.WND_PROP_TOPMOST, 1) # set the window to be always on top
    cv2.imshow(window,img_to_show)
    cv2.waitKey(1)
    return window

# def play_video(frame_list, fps=240, window='image', retention_time = 1000):
#     print('Playing video...', end='')
#     step = 1/fps
#     frmN = 0
#     t0 = time.time()
#     t_seq = []
#     t_play = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
#     for i,frame in enumerate(frame_list):
#         curr_time = time.time()
#         t_theo = i*step 
#         while curr_time-t0 < t_theo:
#             curr_time = time.time()
#         cv2.imshow(window,frame)
#         frmN += 1
#         t_seq.append((1000*(curr_time-t0))) # time in ms
#         cv2.waitKey(1)
#     t1 = time.time()
#     cv2.waitKey(max(retention_time, 1))
#     cv2.destroyWindow(window)
#     cv2.waitKey(1)
#     t_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
#     playFPS = frmN/(t1-t0)
#     interval = np.diff(t_seq)
#     print('done.', end=' ')
#     return playFPS, interval, t_play, t_end
def play_video(frame_list, fps=240, window='image', retention_time=1000):
    """
    Play video frames at the given FPS in real speed by displaying the nearest frame to the theoretical time.
    
    Parameters:
        frame_list (list): List of frames to play.
        fps (int): Target frames per second.
        window (str): Name of the display window.
        retention_time (int): Time to retain the last frame (in milliseconds).
    
    Returns:
        tuple: (playFPS, interval, t_play, t_end)
    """
    print('Playing video...', end='')
    step = 1 / fps  # Time per frame in seconds
    frmN = 0
    t0 = time.time()
    t_seq = []
    t_play = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

    for i in range(len(frame_list)):
        curr_time = time.time()
        t_theo = i * step

        # Wait until the theoretical time for the current frame
        while curr_time - t0 < t_theo:
            curr_time = time.time()

        # Calculate the nearest frame index to the theoretical time
        nearest_frame_index = min(len(frame_list) - 1, round((curr_time - t0) * fps))
        cv2.imshow(window, frame_list[nearest_frame_index])

        frmN += 1
        t_seq.append(1000 * (curr_time - t0))  # Time in ms
        cv2.waitKey(1)

    t1 = time.time()
    cv2.waitKey(max(retention_time, 1))
    cv2.destroyWindow(window)
    cv2.waitKey(1)
    t_end = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    playFPS = frmN / (t1 - t0)
    interval = np.diff(t_seq)
    print('done.', end=' ')
    return playFPS, interval, t_play, t_end

def write_video_log(log_path, real_fps, read_fps, r2v, t_play, t_end, LED_state, duration):
    print('Elapsed: {:.3f} s'.format(duration)) # not including retention time
    print('Read fps = {:.2f}'.format(read_fps))
    print('Real fps = {:.2f}'.format(real_fps))
    print('LED state: {}'.format(LED_state))
    with open(log_path,'a') as log: # save the log file
        log.write('r/v = {} ms\n'.format(r2v))
        log.write('Starting playing time: {}\n'.format(t_play))
        log.write('Done playing time: {}\n'.format(t_end)) # including retention time

        log.write('Read fps = {:.2f}\n'.format(read_fps))
        log.write('Real fps = {:.2f}\n'.format(real_fps))
        log.write('LED state: {}\n'.format(LED_state))
        log.write('\n')
    return


# def SetUpSerialPort(board_type='Arduino Uno', **kwargs):
#     Port = ''
#     port_list = list(serial.tools.list_ports.comports())
#     port_names = [None]*len(port_list)
#     port_num = 0
#     ser = ''
#     for i, port in enumerate(port_list):
#         port_name = port.device
#         port_names[i] = port_name
#         if port.description.find(board_type) != -1:
#             port_num += 1
#             Port = port_name
#     if port_num == 1:
#         print('{} is found on {}'.format(board_type,Port))
#         ser = serial.Serial(port=Port,**kwargs)
#     elif port_num > 1:
#         raise ValueError('More than one {} is connected'.format(board_type))
#     else:
#         print('\n\033[33mNo {} is connected.\nSerial communication is unavailable.\033[0m\n'.format(board_type))
#     return ser
def SetUpSerialPort(board_type='Arduino Uno', baud_rate = 9600, require_confirm=False, **kwargs):
    current_os = platform.system()
    Port = ''
    port_list = list(serial.tools.list_ports.comports())
    port_names = [None]*len(port_list)
    port_num = 0
    ser = ''
    
    for i, port in enumerate(port_list):
        port_name = port.device
        port_names[i] = port_name
        if current_os == 'Windows':
            if port.description.find(board_type) != -1:
                port_num += 1
                Port = port_name
        elif current_os == 'Darwin' or current_os == 'Linux':
            if board_type != 'Arduino':
                board_type = 'Arduino'
                print('Detailed Arduino board cannot be recognized on Mac or Linux. Searching for all "Arduino" boards.')
            if port.manufacturer != None and port.manufacturer.find(board_type) != -1:
                port_num += 1
                Port = port_name
    if port_num == 1:
        print('\n{} is found on {}'.format(board_type,Port))
        if require_confirm:
            answer = input('\nDo you confirm using this port? (Y/n): ')
            if not (answer == 'Y' or answer == 'y'):
                raise ValueError('Port is not confirmed.')
        print('\nBuilding serial connection...')
        ser = serial.Serial(port=Port,baudrate=baud_rate, **kwargs)
        time.sleep(2)
    elif port_num > 1:
        raise ValueError('More than one {} is connected'.format(board_type))
    else:
        print('\n\033[33mNo {} is connected.\nSerial communication is unavailable.\033[0m\n'.format(board_type))
    return ser

def LED_check(LED_state, ser):
    if LED_state:
        print('\nThe LEDs were ON. Please turn OFF before setting timer.')
        return
    elif ser == '':
        print('\nSerial communication is unavailable. LED cannot be turned on.\n')
        return
    else:
        return 0

def LED_switch(LED_state,ser,log_path,turn_on=None):
    t_timeout = 5000
    if ser == '':
        print('\nSerial communication is unavailable. LED state cannot be changed.\n')
        return LED_state
    if turn_on is not None:
        if turn_on and LED_state: # if LED is already on
            return LED_state
        elif (not turn_on) and (not LED_state): # if LED is already off
            return LED_state
    if LED_state:
        ser.write(b'off\n')
    else:
        ser.write(b'on\n')
    t_led = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    LED_state = 1 - LED_state
    t_arduino = time.time()
    while True:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout: # wait for 5 seconds
            raise TimeoutError('Arduino timeout')
        feedback = ser.readline()
        if feedback != b'':
            feedback = feedback.decode()[:-1]
            if feedback == 'Light ON' or feedback == 'Light OFF':
                t_led_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(log_path,'a') as log: # save the log file
                    log.write('{} at {}\n'.format(feedback, t_led))
                    log.write('Feedback {} at {}\n'.format(feedback, t_led_fb))
                    log.write('\n')
                print(feedback)
                break
            else:
                raise ValueError(feedback)
    return LED_state


def LED_timer(LED_state,ser,log_path,timer,delay=0,wait_for_feedback=True):
    if LED_check(LED_state, ser) != 0: return
    t_timeout = timer + 5
    if delay <= 0:
        delay = 0
        print(f'LED timer: {timer:.3f} s (Press <Ctrl+C>) to interrupt)')
    elif delay > 0:
        print(f'Delayed LED timer: {timer:.3f} s after {delay:.3f} s delay (Press <Ctrl+C>) to interrupt)')
        
    cmd_t = 'r' + str(int(timer*1000)) + 'd' + str(int(delay*1000)) + '\n'
    ser.write(cmd_t.encode('utf-8'))
    t_on = datetime.now() + timedelta(seconds=delay)
    t_off = t_on + timedelta(seconds=timer)
    t_on = t_on.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    t_off = t_off.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    if wait_for_feedback:
        t_arduino = time.time()
        while True:
            t_wait = time.time() - t_arduino
            if t_wait > t_timeout:
                raise TimeoutError('Arduino timeout')
            if LED_state and timer > 1: # if timer is longer than 1 second
                current_time = time.time()
                remaining = timer-(current_time-t_start)
                # Print countdown regularly
                if not hasattr(LED_timer, 'last_print_time') or current_time - LED_timer.last_print_time >= 0.1:
                    if remaining > 0.05:  # Normal countdown
                        print(f'\rLED left: {remaining:.1f} s (Press <Ctrl+C>) to interrupt)', end='      ')
                    else:  # Final 0.0
                        print('\rLED left: 0.0 s', end='      ')
                    LED_timer.last_print_time = current_time
            if ser.inWaiting() > 0:
                fb = ser.readline().decode()[:-1]
                if fb == 'Light ON':
                    t_on_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    LED_state = 1
                    t_start = time.time()
                    print(fb)
                elif fb == 'Light OFF':
                    t_off_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    LED_state = 0
                    print('\n'+fb)
                    break
                else:
                    raise ValueError('Wrong feedback from Arduino: {}'.format(fb))
    else:
        print('\033[30mNot listening to the feedbacks from Arduino\033[0m')
    with open(log_path,'a') as log:
        log.write('LED timer: {} s\n'.format(timer))
        log.write('Light ON at {}\n'.format(t_on))
        log.write('Light OFF at {}\n'.format(t_off))
        if wait_for_feedback:
            log.write('Feedback Light ON at {}\n'.format(t_on_fb))
            log.write('Feedback Light OFF at {}\n'.format(t_off_fb))
        log.write('\n')
    return 0


def LED_pulse(LED_state,ser,log_path,duration,frequency,pulse_width):
    if LED_check(LED_state, ser) != 0: return
    t_timeout = duration + 5
    cmd_p = 'p' + str(int(duration*1000)) + 'f' + str(int(frequency*1000)) + 'w' + str(pulse_width) + '\n'
    ser.write(cmd_p.encode('utf-8'))
    t_on = datetime.now()
    t_off = t_on + timedelta(seconds=duration)
    t_on = t_on.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    t_off = t_off.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print('LED pulsing for {:.3f} s at {:.3f} Hz with {:d} ms pulse width'.format(duration,frequency,pulse_width))
    t_arduino = time.time()
    while True:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout:
            raise TimeoutError('Arduino timeout')
        if LED_state and duration > 1: # if timer is longer than 1 second
            current_time = time.time()
            remaining = duration-(current_time-t_start)
            # Print countdown regularly
            if not hasattr(LED_pulse, 'last_print_time') or current_time - LED_pulse.last_print_time >= 0.1:
                if remaining > 0.05:  # Normal countdown
                    print(f'\rLED left: {remaining:.1f} s (Press <Ctrl+C>) to interrupt)', end='      ')
                else:  # Final 0.0
                    print('\rLED left: 0.0 s', end='      ')
                LED_pulse.last_print_time = current_time
        if ser.inWaiting() > 0:
            fb = ser.readline().decode()[:-1]
            if fb == 'Pulsing ON':
                t_on_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                LED_state = 1
                t_start = time.time()
                print(fb)
            elif fb == 'Pulsing OFF':
                t_off_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                LED_state = 0
                print('\n'+fb)
                break
            else:
                raise ValueError('Wrong feedback from Arduino: {}'.format(fb))
    with open(log_path,'a') as log:
        log.write('LED Pulsing: {} s\n'.format(duration))
        log.write('Frequency: {} Hz\n'.format(frequency))
        log.write('Pulse width: {} ms\n'.format(pulse_width))
        log.write('Pulsing ON at {}\n'.format(t_on))
        log.write('Pulsing OFF at {}\n'.format(t_off))
        log.write('Feedback Pulsing ON at {}\n'.format(t_on_fb))
        log.write('Feedback Pulsing OFF at {}\n'.format(t_off_fb))
        log.write('\n')
    return 0


def pump_switch(pump_state, ser, log_path, turn_on=None):
    """Control the air pump (turn on/off)"""
    t_timeout = 5000
    if ser == '':
        print('\nSerial communication is unavailable. Pump state cannot be changed.\n')
        return pump_state
    if turn_on is not None:
        if turn_on and pump_state:  # if pump is already on
            return pump_state
        elif (not turn_on) and (not pump_state):  # if pump is already off
            return pump_state
    
    if pump_state:
        ser.write(b'pump:off\n')
    else:
        ser.write(b'pump:on\n')
    t_pump = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    pump_state = 1 - pump_state
    t_arduino = time.time()
    while True:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout:  # wait for 5 seconds
            raise TimeoutError('Arduino timeout')
        feedback = ser.readline()
        if feedback != b'':
            feedback = feedback.decode()[:-1]
            if feedback == 'Pump ON' or feedback.startswith('Pump OFF'):
                t_pump_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(log_path, 'a') as log:  # save the log file
                    log.write('{} at {}\n'.format(feedback, t_pump))
                    log.write('Feedback {} at {}\n'.format(feedback, t_pump_fb))
                    log.write('\n')
                print(feedback)
                break
            elif feedback.startswith('Warning:'):
                print('\033[33m' + feedback + '\033[0m')
            else:
                raise ValueError(feedback)
    return pump_state


def set_pump_value(ser, log_path, value):
    """Set the pump power value (0-255)"""
    if ser == '':
        print('\nSerial communication is unavailable. Pump value cannot be set.\n')
        return
    
    # Validate the pump value
    try:
        value = int(value)
        if value < 0 or value > 255:
            print('\033[31mPump value must be between 0-255\033[0m')
            return
    except ValueError:
        print('\033[31mInvalid pump value. Must be an integer between 0-255\033[0m')
        return
    
    t_timeout = 5000
    cmd = 'pump:value:{}\n'.format(value)
    ser.write(cmd.encode('utf-8'))
    t_pump = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    t_arduino = time.time()
    while True:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout:  # wait for 5 seconds
            raise TimeoutError('Arduino timeout')
        feedback = ser.readline()
        if feedback != b'':
            feedback = feedback.decode()[:-1]
            if feedback.startswith('Pump value set to'):
                t_pump_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(log_path, 'a') as log:  # save the log file
                    log.write('{} at {}\n'.format(feedback, t_pump))
                    log.write('Feedback received at {}\n'.format(t_pump_fb))
                    log.write('\n')
                print(feedback)
                return 0
            elif feedback.startswith('Invalid pump value'):
                print('\033[31m' + feedback + '\033[0m')
                return 1
            else:
                raise ValueError(feedback)


def shock_switch(shock_state, ser, log_path, turn_on=None):
    """
    Control the shock pulses (turn on/off)
    Waits for immediate feedback confirming state change
    
    Parameters:
        shock_state (bool): Current shock state (True=on, False=off)
        ser: Serial port object
        log_path (str): Path to log file
        turn_on (bool, optional): Force on/off state. Defaults to None (toggle).
        
    Returns:
        bool: New shock state
    """
    if ser == '':
        print('\nSerial communication is unavailable. Shock state cannot be changed.\n')
        return shock_state
        
    # Check if we need to change state
    if turn_on is not None:
        if turn_on and shock_state:  # if shock is already on
            return shock_state
        elif (not turn_on) and (not shock_state):  # if shock is already off
            return shock_state
    
    # Send command to Arduino
    if shock_state:
        ser.write(b'shock:off\n')
        expected_feedback = "Shock pulses OFF"  # Match exact string from Arduino
    else:
        ser.write(b'shock:on\n')
        expected_feedback = "Shock pulses ON"  # Match exact string from Arduino
    
    # Log action time
    t_shock = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # Wait for immediate feedback from Arduino confirming state change
    t_timeout = 5  # timeout in seconds
    t_arduino = time.time()
    feedback_received = False
    
    while not feedback_received:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout:
            print(f'\033[33mWarning: No feedback received from Arduino after {t_timeout}s. Shock state may not have changed.\033[0m')
            break
            
        if ser.inWaiting() > 0:
            feedback = ser.readline().decode()[:-1]
            if feedback == expected_feedback:
                t_shock_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(log_path, 'a') as log:
                    log.write(f'Sent command for {expected_feedback} at {t_shock}\n')
                    log.write(f'Received confirmation: "{feedback}" at {t_shock_fb}\n')
                    log.write('\n')
                print(f"Received: {feedback}")
                feedback_received = True
            else:
                print(f'\033[33mReceived unexpected response: "{feedback}" (waiting for "{expected_feedback}")\033[0m')
    
    # Update shock state ONLY if we received confirmation
    if feedback_received:
        shock_state = 1 - shock_state
    else:
        with open(log_path, 'a') as log:
            log.write(f'Warning: Failed to confirm shock state change at {t_shock}\n')
            log.write('\n')
    
    return shock_state


def valve_switch(valve_name, valve_state, ser, log_path, turn_on=None):
    """
    Control the valves (air, odor_a, odor_b)
    valve_name: 'air', 'odor_a', or 'odor_b'
    valve_state: current state of the valve (0=off, 1=on)
    turn_on: None, True, or False (to set a specific state)
    """
    if valve_name not in ['air', 'odor_a', 'odor_b']:
        print('\033[31mInvalid valve name. Must be "air", "odor_a", or "odor_b"\033[0m')
        return valve_state
    
    t_timeout = 5  # timeout in seconds (reduced from 5000 ms)
    if ser == '':
        print('\nSerial communication is unavailable. Valve state cannot be changed.\n')
        return valve_state
        
    if turn_on is not None:
        if turn_on and valve_state:  # if valve is already on
            return valve_state
        elif (not turn_on) and (not valve_state):  # if valve is already off
            return valve_state
    
    # Prepare command
    if valve_state:
        cmd = '{}:off\n'.format(valve_name)
    else:
        cmd = '{}:on\n'.format(valve_name)
        
    # Send command
    ser.write(cmd.encode('utf-8'))
    t_valve = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # Log the command being sent
    with open(log_path, 'a') as log:
        log.write('Sent {} command at {}\n'.format(cmd.strip(), t_valve))

    # Wait for feedback with reasonable timeout
    t_arduino = time.time()
    while True:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout:  # wait for 5 seconds
            print('\033[33mWarning: No feedback received from Arduino. Command may not have been processed.\033[0m')
            # Don't update the state since we don't know if command succeeded
            return valve_state
            
        if ser.inWaiting() > 0:
            feedback = ser.readline().decode()[:-1]
            if feedback != '':
                # Handle different types of feedback
                if feedback.endswith('valve OPEN') or feedback.endswith('valve CLOSED'):
                    t_valve_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    with open(log_path, 'a') as log:
                        log.write('{} at {}\n'.format(feedback, t_valve))
                        log.write('Feedback {} at {}\n'.format(feedback, t_valve_fb))
                        log.write('\n')
                    print(feedback)
                    
                    # Update the valve state based on the feedback
                    new_valve_state = 1 if 'OPEN' in feedback else 0
                    return new_valve_state
                    
                elif feedback.startswith('Warning:'):
                    # Print warning and continue waiting for final status
                    print('\033[33m' + feedback + '\033[0m')
                    
                    # If the warning indicates failure, don't change the state
                    if "Cannot open valve - Pump is OFF" in feedback:
                        return valve_state
                else:
                    # Unexpected feedback
                    print('\033[33mUnexpected response: {}\033[0m'.format(feedback))


def quit_all_operations(ser, log_path):
    """Send quit command to Arduino to terminate all operations"""
    if ser == '':
        print('\nSerial communication is unavailable. Cannot send quit command.\n')
        return 1
    
    t_timeout = 5  # timeout in seconds
    ser.write(b'quit\n')
    t_quit = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print('Sending quit command to Arduino...')
    
    # Wait for feedback from Arduino
    t_arduino = time.time()
    while True:
        t_wait = time.time() - t_arduino
        if t_wait > t_timeout:
            raise TimeoutError('Arduino timeout')
        if ser.inWaiting() > 0:
            fb = ser.readline().decode()[:-1]
            if fb == "All operations terminated":
                t_quit_fb = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                with open(log_path, 'a') as log:  # save the log file
                    log.write('Quit command sent at {}\n'.format(t_quit))
                    log.write('Feedback: {} at {}\n'.format(fb, t_quit_fb))
                    log.write('\n')
                print('All operations on Arduino terminated successfully.')
                break
            else:
                raise ValueError(f'Wrong feedback from Arduino: {fb}')
    
    return 0


def time_delay(delay,prefix='left:',suffix='s', print_left=True):
    '''
    delay in seconds
    prefix: string before the time left to print
    suffix: string after the time left to print
    print_left: whether to print the notice of time left
    '''
    t_start = time.time()
    while True:
        t_wait = time.time() - t_start
        if t_wait >= delay:
            break
        if print_left: print(f'\r{prefix} {delay-t_wait:.2f} {suffix}',end='')
    if print_left: print()
    return 0

def GenerateLoomingImgs(**kwargs):
    '''Generate looming images for looming experiment'''
    options = {
        'r2v': 320, # value of r/v, in ms
        'frameRate': 240, # frame rate
        'stop_size': 2e10, # in ms, 200 for the largest ellipse, larger for full screen
        'real_distance': 5000, # in mm
        'r_object': 100, # radius of object
        'Distance': 100, # distance from screen to flies
        'ap': R"D:\GY_GUA\controller\pictrues", # absolute path of looming files
        't_step': None, # time step
        'tm': None, # total time, move starting with a 5 degree angle
        'bg_color': (0, 0, 0), # background color, default is black
        'dpi': 120, # dpi of the output image
        'fig_size': (16, 9), # figure size
    }
    options.update(kwargs)
    
    if options['t_step'] is None:
        options['t_step'] = 1000/options['frameRate']
    if options['tm'] is None:
        options['tm'] = -options['r2v']/np.tan(np.deg2rad(2.5))
    op = SimpleNamespace(**options)
    
    if os.path.exists(op.ap):
        shutil.rmtree(op.ap)
    os.mkdir(op.ap)

    ellis = []
    t_series = np.arange(op.tm, 0, op.t_step)
    for t in t_series:  # each picture
        radius = op.Distance*np.tan((np.arctan(-op.r2v/t)))
        b = radius # short axis
        a = np.sqrt(2)*radius # long axis
        if b > op.stop_size: break # stop when the ellipse is too large
        e = Ellipse(xy=(0, 0), width=2*a, height=2*b, facecolor=np.array([0, 0, 0])/255)
        ellis.append(e)

    for i, e in enumerate(ellis):
        fig, ax = plt.subplots(
            tight_layout=True,
            subplot_kw={'aspect': 'equal'},
            figsize=op.fig_size,
            dpi=op.dpi,
        )
        ax.set_xlim(-400, 400)
        ax.set_ylim(-200, 200)
        ax.set_axis_off()
        ax.add_artist(e)
        fig.savefig(os.path.join(op.ap, 'pic_{}.png'.format(i+1)),
                    bbox_inches='tight', facecolor=op.bg_color)
        plt.close(fig)
        print('\r', i+1, '/', len(ellis), end='')
    return options


def img2video(img_dir, video_dir, fps=240, size=None):
    '''convert images to video
    img_dir: directory of images
    video_dir: directory of video to be saved
    fps: frame rate
    size: size of the video, default is the same as the first image
    '''
    img_array = []
    for i in range(len(os.listdir(img_dir))):
        filename = 'pic_{}.png'.format(i+1)
        print('\rread', i+1, '/', len(os.listdir(img_dir)), end='')
        img = cv2.imread(os.path.join(img_dir, filename))
        height, width, layers = img.shape
        if size is None:
            size = (width, height)
        img_array.append(img)
    print()
    out = cv2.VideoWriter(
        video_dir, cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
    for i in range(len(img_array)):
        out.write(img_array[i])
        print('\rwrite', i+1, '/', len(img_array), end='')
    out.release()
    return 0

