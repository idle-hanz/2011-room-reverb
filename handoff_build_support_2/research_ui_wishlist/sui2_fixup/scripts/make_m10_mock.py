"""Mock m10: Mic tab with the three per-mic graphs always visible (here Measured, read-only) and the Source plane below them.
Composited from Build's 09:56 shots (mic_measured_1600.png top + Source plane, mic_user_1600.png trio). MOCK, not a screenshot."""
from PIL import Image, ImageDraw, ImageFont
S='/workspace/build_support_2/snapshot_2026-10-03_1415/shots_new/'
F=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',14); FB=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',14)
u=Image.open(S+'mic_user_1600.png').convert('RGB'); m=Image.open(S+'mic_measured_1600.png').convert('RGB')
top=m.crop((0,0,1600,1282)); trio=u.crop((0,2040,1600,2650)).copy(); sp=m.crop((0,1282,1600,2088)).copy()
d=ImageDraw.Draw(trio); bg=trio.getpixel((40,8))
# replace the "Each capsule" summary line with a panel title + lock note
d.rectangle((24,6,1560,34),fill=bg)
d.text((32,9),"EACH MIC",font=FB,fill=(150,160,175)); d.text((140,9),"one mic each, not the combined pattern",font=F,fill=(120,130,145))
d.rounded_rectangle((1290,6,1560,32),radius=10,fill=(70,52,10)); d.text((1302,9),"read-only · preset pattern",font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',15),fill=(245,190,60))
for cx,txt in ((284,"Cardioid · −55° · preset law"),(798,"Cardioid · 0° · preset law"),(1314,"Cardioid · +55° · preset law")):
    d.rectangle((cx-200,2590-2040-12,cx+200,2590-2040+12),fill=trio.getpixel((cx,2590-2040-16)))
    w=d.textlength(txt,font=F); d.text((cx-w/2,2590-2040-10),txt,font=F,fill=(150,160,175))
y=2629-2040; d.rectangle((24,y-14,1570,y+14),fill=bg)
d.text((32,y-11),"Measured: the preset owns the pattern (Shure SM57 = cardioid). Drag the amber front to aim. Switch Colour to User defined to shape the pattern.",font=F,fill=(235,170,60))
# Source plane: drop the old foot hint (it talked about the hidden trio)
d2=ImageDraw.Draw(sp); y2=2029-1282; c2=sp.getpixel((1500,y2)); d2.rectangle((24,y2-14,1570,y2+14),fill=c2)
out=Image.new('RGB',(1600,top.height+trio.height+12+sp.height),(13,16,20))
out.paste(top,(0,0)); out.paste(trio,(0,top.height+6)); out.paste(sp,(0,top.height+trio.height+12))
dd=ImageDraw.Draw(out); dd.rectangle((0,0,1600,4),fill=(245,190,60))
dd.text((660,4),"MOCK m10 · Measured · per-mic graphs always shown, Source plane below",font=F,fill=(245,190,60))
out.save('../mock/m10_mic_each_always.png'); print(out.size)
