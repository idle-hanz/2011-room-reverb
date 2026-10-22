"""Render mock HTML files to PNG with headless Chrome (full page)."""
import sys, glob, os
from playwright.sync_api import sync_playwright
S='/workspace/build_support_2/research_ui_wishlist/mock/src/'; O='/workspace/build_support_2/research_ui_wishlist/mock/'
files=sys.argv[1:] or sorted(glob.glob(S+'m*.html'))
with sync_playwright() as p:
    b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True)
    pg=b.new_page(viewport={'width':1636,'height':900})
    for f in files:
        f=f if f.startswith('/') else S+f
        pg.goto('file://'+f); pg.wait_for_timeout(300)
        out=O+os.path.basename(f).replace('.html','.png'); pg.screenshot(path=out,full_page=True); print(out)
    b.close()
