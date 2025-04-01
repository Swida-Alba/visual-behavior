import os
from LoomingFunc import GenerateLoomingImgs, img2video

bgc = 'b' # 'w' for white, 'b' for blue
shape = 'circle' # 'full' for end with full screen, 'circle' for end with the largest circle
fps = 240
dpi = 40 # no less than 120 for the best performance
save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '_'.join([bgc, shape, str(fps)+'Hz', str(dpi)+'dpi']))

rvs = [20, 40, 80, 160, 320]

if __name__ == "__main__":
    if not os.path.exists(save_dir): os.mkdir(save_dir)
    if shape == 'full':
        end_size = 2000
    elif shape == 'circle':
        end_size = 200
    if bgc == 'w':
        bgc = (1,1,1)
    elif bgc == 'b':
        bgc = (0,0,1)
    
    for rv in rvs:
        options = GenerateLoomingImgs(r2v=rv,bg_color=bgc,stop_size=end_size,dpi=dpi,frameRate=fps,save_dir=save_dir)
        img2video(img_dir=options['ap'], video_dir=os.path.join(save_dir,'rv_'+str(rv)+'.mp4'), fps=options['frameRate'])
        print('\nr/v = '+str(rv)+' done')