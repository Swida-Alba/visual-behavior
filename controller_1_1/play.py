from StimulationAssistant import VideoDelivery
player = VideoDelivery(
    video_dir = R'looming_videos\w_circle_240Hz_120dpi',
    stim_name = 'r/v',
    stimulus = '40', # ms
    LED_retention = 2000, # ms
    video_retention = 1000, # ms,
    shut_backgroud = True,
    
)
player.start_journey()