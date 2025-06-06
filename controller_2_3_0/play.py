from StimulationAssistant import StimController

player = StimController(
    video_dir = R'looming_videos/small_test',
    stim_name = 'r/v',
    stimulus = '20', # ms
    LED_retention = 2000, # ms
    video_retention = 1000, # ms,
    shut_backgroud = True,
    board_type = 'Arduino',
    
    pulse_span = 10, # seconds
    pulse_frequency = 1, # Hz
    pulse_width = 100, # ms
    update_pulse = False,
)

player.start_journey()
