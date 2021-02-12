# QuickAnchors.py
# I use this script by:
# $ ln -s $PWD/QuickAnchors.py $HOME/.config/fontforge/QuickAnchors.py
# Then it appears as "QuickAnchors" in the FontForge «Tools» menu.

# You need (Arch): python-pillow python-cairosvg tk fontforge

import fontforge
import tkinter as tk
from tempfile import mktemp
from PIL import Image, ImageTk
import os, sys
import cairosvg
from io import BytesIO

from xml.etree import ElementTree

import re
import random
import string

# This implementation isn't /great/. I wrote it quickly to solve my problem. Here's how it works:
# * Use FontForge to output an SVG for the glyph.
# * Read in the viewBox from the SVG.
# * Rasterize SVG with Cairo.
# * Use Tkinter to display a glyph for every glyph in that matches `regexp`
# * When user hovers mouse, show floating accent according to glyph in ACCENT_UNI
# * When user clicks, write row with glyphname, and X, Y glyph position.
# * You may want to adjust the numbers in the function capy_for_letter and the classes below:

CAPS = set(string.ascii_uppercase)
HAS_ASCENDERS = set("bdfhklt")
NO_ASCENDERS  = set(string.ascii_lowercase) - HAS_ASCENDERS
REPLACEMENTS = {"i": "dotlessi", "i.low": "dotlessi.low", "i.high": "dotlessi.high",
                "j": "dotlessj", "j.low": "dotlessj.low", "j.high": "dotlessj.high"}
for v in REPLACEMENTS.values():
    NO_ASCENDERS.add(v)

ACCENT_UNI = "uni0302"
OUTFILE = "build_data/top.tsv"

# How far off on the x axis is the origin?
def viewBox_diff(glyph, svgfn):
    with open(svgfn) as f:
        etree_ = ElementTree.ElementTree(file=f)
        viewbox = etree_.getroot().get('viewBox').split()
    (x, y, w, h) = [int(e) for e in viewbox]
    return (x, w-glyph.width)

# Source: https://stackoverflow.com/a/14910894 CC BY-SA 3.0 StackOverflow user @Rachel Gallen
def center_window(root, width, height):
    # get screen width and height
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()

    # calculate position x and y coordinates
    x = (screen_width/2) - (width/2)
    y = (screen_height/2) - (height/2)
    root.geometry('%dx%d+%d+%d' % (width, height, x, y))

def svg_to_PILImage(svgfn):
    ret = BytesIO()
    cairosvg.svg2png(url=svgfn, write_to=ret)
    image = Image.open(ret)
    return image

def combine_images(im, im2, x, y):
    im = im.copy()
    xs, ys = im2.size
    im.paste(im2, (x, y), im2)
    return im

# If you want to be able to move the anchor anywhere, just make this function always return False.
# Set them negative for bottom accents. :)
def capy_for_letter(gn):
    letter = gn.split(".")[0]
    if letter in CAPS or letter in HAS_ASCENDERS:
        return 650
    elif letter in NO_ASCENDERS:
        return 400
    else:
        return False

# takes name of a temporary file where the image is
def pop_window_for_image(font, glyph, im, imaccent, vbdiff, vbdiffa):
    outfile = open(OUTFILE, "a+")

    tkroot = tk.Tk()
    w = tk.Frame()
    tkimage = ImageTk.PhotoImage(im)
    canvas = tk.Canvas(w, width = tkimage.width(), height = tkimage.height())
    image_on_canvas = canvas.create_image(0, 0, anchor=tk.NW, image=tkimage)
    center_window(tkroot, tkimage.width(), tkimage.height())
    should_exit = should_prev = False

    def motion(event):
        nonlocal vbdiff, vbdiffa, im, imaccent, canvas, image_on_canvas, tkimage, glyph
        capy = capy_for_letter(glyph.glyphname)
        combined = combine_images(im, imaccent, event.x+vbdiffa[0], -capy if capy else (event.y-font.ascent))
        tkimage = ImageTk.PhotoImage(combined)
        canvas.itemconfig(image_on_canvas, image=tkimage)
        canvas.update()

    def click(event):
        nonlocal vbdiff, tkroot, glyph, outfile
        x = event.x + vbdiff[0]
        y = -(event.y - font.ascent)
        capy = capy_for_letter(glyph.glyphname)
        outfile.write("{}\t{}\t{}\n".format(glyph.glyphname, x, capy if capy else y))
        tkroot.destroy()

    def quit(_):
        nonlocal tkroot, should_exit
        should_exit = True
        tkroot.destroy()

    def prev(_):
        nonlocal tkroot, should_prev
        should_prev = True
        tkroot.destroy()

    def next_(_):
        nonlocal tkroot
        tkroot.destroy()

    tkroot.bind("<Motion>", motion)
    tkroot.bind("<Button-1>", click)
    tkroot.bind("p", prev)
    tkroot.bind("n", next_)
    tkroot.bind("q", quit)
    w.pack()
    canvas.pack()
    w.mainloop()

    outfile.close()
    return (should_exit, should_prev)

def main(_, font):
    doneglyphs = list()

    if os.path.exists(OUTFILE):
        with open(OUTFILE) as f:
            for line in f.readlines():
                doneglyphs.append(line.split("\t")[0])

    font = fontforge.activeFont()

    font.ascent += 200

    # we must write an SVG because the PNG output doesn't preserve left/right bearings when glyph overflows bearings. my fault partially lol
    tempf = mktemp(suffix=".svg")
    tempaccentf = mktemp(suffix=".svg")

    accent = font[ACCENT_UNI]
    accent.export(tempaccentf)
    vbdiffa = viewBox_diff(accent, tempaccentf)
    imaccent = svg_to_PILImage(tempaccentf)

    regexp = re.compile(r"^[a-zA-Z](\.[a-zA-Z0-9_]+)?$")

    glyphs = [g.glyphname if g.glyphname not in REPLACEMENTS else REPLACEMENTS[g.glyphname]
              for g in font.glyphs() if re.match(regexp, g.glyphname)]

    # makes it less boring. feel free to comment
    random.shuffle(glyphs)

    if set(doneglyphs) == set(glyphs):
        fontforge.logWarning("QuickAnchors: No glyphs which match the criteria and aren't done")

    def process_glyph(i, glyph):
        nonlocal font, doneglyphs, accent, imaccent, regexp, glyphs, tempf
        should_exit = should_prev = False

        glyph = font[glyph]

        if glyph.glyphname in doneglyphs:
            print("Warning: skipping {}".format(repr(glyph)), file=sys.stderr)
        else:
            glyph.width += 300
            glyph.export(tempf, pixelsize=font.em)
            vbdiff = viewBox_diff(glyph, tempf)
            im = svg_to_PILImage(tempf)
            (should_exit, should_prev) = pop_window_for_image(font, glyph, im, imaccent, vbdiff, vbdiffa)
            os.remove(tempf)
            glyph.width -= 300

        if should_exit:
            return False
        elif should_prev and i != 0:
            return process_glyph(i-1, glyphs[i-1])
        elif should_prev:
            return process_glyph(0, glyphs[0])
        elif i+1 == len(glyphs):
            return True
        else:
            return process_glyph(i+1, glyphs[i+1])

        return True

    process_glyph(0, glyphs[0])

fontforge.registerMenuItem(main, None, None, "Font", None, "QuickAnchors")
