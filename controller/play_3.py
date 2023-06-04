from LoomingInit import LoomingParameters
lp = LoomingParameters(
    r2v=40, # ms
    backgroud_color='b', # 'w' for white, 'b' for blue
    shape='circle', # 'full' for end with full screen, 'circle' for end with the largest circle
    LED_retention=2000, # ms
    loom_retention=1000, # ms
    dpi=120,
)

lp.start_journey()