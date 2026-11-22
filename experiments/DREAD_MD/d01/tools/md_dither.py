import numpy as np
DAC=np.array([0,52,87,116,144,172,206,255],float)
def dither(rgb,colors,mask=None):
 rgb=np.asarray(rgb,float);colors=np.asarray(colors,float);h,w=rgb.shape[:2];work=rgb.copy();out=np.zeros((h,w),np.uint8)
 if mask is None:mask=np.ones((h,w),bool)
 for y in range(h):
  for x in range(w):
   if not mask[y,x]:continue
   v=np.clip(work[y,x],0,255);i=int(((colors-v)**2).sum(1).argmin());out[y,x]=i;err=np.clip(v-colors[i],-64,64)
   for dx,dy,k in [(1,0,7/16),(-1,1,3/16),(0,1,5/16),(1,1,1/16)]:
    xx,yy=x+dx,y+dy
    if 0<=xx<w and yy<h and mask[yy,xx]:work[yy,xx]+=err*k
 return out
