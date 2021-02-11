# `QuickAnchors.py` — quickly add anchors in FontForge

I use this script by:
```bash
ln -s $PWD/QuickAnchors.py $HOME/.config/fontforge/QuickAnchors.py
```
Then it appears as "QuickAnchors" in the FontForge «Tools» menu.

You need (Arch): `python-pillow` `python-cairosvg` `tk` `fontforge`

Further documentation can be had by reading the source code :-)

Also, the script doesn't read the anchor of the accent you are placing. It assumes the anchor will be (0, 0).

# Output

Output is tab-separated values like:

```tsv
glyph	x	y
a	0	0
b	0	100
```

Up to you to put these into your font. The font I made this for isn't using FontForge's anchors.
