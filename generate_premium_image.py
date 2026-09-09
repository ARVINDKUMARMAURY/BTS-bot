"""
Generates assets/premium_features.png — a BTS-branded premium features comparison
poster, styled after the BAKA Premium Features card.
Run once at build time: python3 generate_premium_image.py
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1500

BG_TOP = (18, 10, 30)
BG_BOTTOM = (8, 6, 14)
PANEL = (26, 16, 40)
PANEL_LINE = (60, 30, 90)
GOLD = (230, 190, 255)
PURPLE_TITLE = (200, 140, 255)
GREEN = (110, 230, 130)
WHITE = (235, 235, 245)
GREY = (150, 150, 165)
PINK_BORDER = (190, 80, 200)

FONT_DIR = "/usr/share/fonts/truetype/google-fonts/"
DEJAVU = "/usr/share/fonts/truetype/dejavu/"
EMOJI_FONT_PATH = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"

f_title = ImageFont.truetype(FONT_DIR + "Poppins-Bold.ttf", 54)
f_header = ImageFont.truetype(FONT_DIR + "Poppins-Bold.ttf", 34)
f_row_label = ImageFont.truetype(FONT_DIR + "Poppins-Medium.ttf", 27)
f_row_value = ImageFont.truetype(FONT_DIR + "Poppins-Bold.ttf", 26)
f_footer = ImageFont.truetype(FONT_DIR + "Poppins-Medium.ttf", 22)
f_emoji = ImageFont.truetype(EMOJI_FONT_PATH, 109)  # native bitmap strike size


def emoji_img(char, target_px):
    """Render a color emoji glyph to a small RGBA image at the requested pixel size."""
    canvas = Image.new("RGBA", (136, 136), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)
    d.text((0, 0), char, font=f_emoji, embedded_color=True)
    bbox = canvas.getbbox()
    if bbox:
        canvas = canvas.crop(bbox)
    return canvas.resize((target_px, target_px), Image.LANCZOS)


def paste_emoji(base, char, xy, size=36):
    glyph = emoji_img(char, size)
    base.paste(glyph, xy, glyph)


def vgrad(draw, box, top, bottom):
    x0, y0, x1, y1 = box
    height = y1 - y0
    for i in range(height):
        t = i / max(height - 1, 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        draw.line([(x0, y0 + i), (x1, y0 + i)], fill=(r, g, b))


img = Image.new("RGB", (W, H), BG_TOP)
draw = ImageDraw.Draw(img)
vgrad(draw, (0, 0, W, H), BG_TOP, BG_BOTTOM)

# Outer glowing border panel
margin = 30
draw.rounded_rectangle(
    [margin, margin, W - margin, H - margin], radius=28, outline=PINK_BORDER, width=4
)
draw.rounded_rectangle(
    [margin + 8, margin + 8, W - margin - 8, H - margin - 8], radius=22, outline=(90, 40, 110), width=2
)

# Title
title = "BTS PREMIUM FEATURES"
tb = draw.textbbox((0, 0), title, font=f_title)
tw = tb[2] - tb[0]
title_x = (W - tw) / 2
draw.text((title_x, 70), title, font=f_title, fill=PURPLE_TITLE)
paste_emoji(img, "💎", (int(title_x) - 70, 65), size=58)
paste_emoji(img, "💎", (int(title_x) + tw + 12, 65), size=58)
draw.line([(120, 150), (W - 120, 150)], fill=PINK_BORDER, width=2)

# Table geometry
table_x0, table_x1 = 70, W - 70
table_y0 = 190
row_h = 88
header_h = 70
col1_x = table_x0 + 20      # feature label start
col2_cx = table_x0 + (table_x1 - table_x0) * 0.58   # normal column center
col3_cx = table_x0 + (table_x1 - table_x0) * 0.85   # premium column center

rows = [
    ("👤", "Profile Style", "Normal", "Or Custom"),
    ("🎁", "Daily Reward", "$2000 Verify", "$5,000 No Verify"),
    ("💀", "Kill Earnings", "$100-200, 0-10xp", "$200-400, 10-20xp"),
    ("💰", "Rob Limit", "$10k", "$30k"),
    ("⚔️", "Daily Limit", "200 Kills, 150 Robs", "400 Kills, 300 Robs"),
    ("📜", "Game Taxes", "10%", "5%"),
    ("🛡️", "Protection", "1 Day", "2 Days"),
    ("😎", "Custom Emoji", "—", "/setemoji"),
    ("🛡️", "Check Protection", "—", "/check"),
    ("👛", "Wallet (unrobbable)", "—", "/wallet - save 30%"),
    ("🏆", "Leaderboard", "—", "Premium Badge"),
    ("💎", "Gem Usage", "—", "50 gems / day"),
]

# Header row
header_y = table_y0
draw.rounded_rectangle(
    [table_x0, header_y, table_x1, header_y + header_h], radius=14, fill=(45, 20, 60)
)
draw.text((col1_x, header_y + 18), "Features", font=f_header, fill=WHITE)
hb = draw.textbbox((0, 0), "Normal", font=f_header)
draw.text((col2_cx - (hb[2] - hb[0]) / 2, header_y + 18), "Normal", font=f_header, fill=WHITE)
hb = draw.textbbox((0, 0), "Premium", font=f_header)
draw.text((col3_cx - (hb[2] - hb[0]) / 2, header_y + 18), "Premium", font=f_header, fill=(255, 210, 120))

y = header_y + header_h + 6
for i, (icon, label, normal, premium) in enumerate(rows):
    row_bg = PANEL if i % 2 == 0 else (32, 20, 48)
    draw.rounded_rectangle([table_x0, y, table_x1, y + row_h - 8], radius=10, fill=row_bg)

    icon_y = int(y + (row_h - 8) / 2 - 18)
    paste_emoji(img, icon, (col1_x, icon_y), size=36)
    draw.text((col1_x + 46, y + (row_h - 8) / 2 - 15), label, font=f_row_label, fill=WHITE)

    nb = draw.textbbox((0, 0), normal, font=f_row_value)
    draw.text((col2_cx - (nb[2] - nb[0]) / 2, y + (row_h - 8) / 2 - 14), normal, font=f_row_value, fill=GREY)

    pb = draw.textbbox((0, 0), premium, font=f_row_value)
    draw.text((col3_cx - (pb[2] - pb[0]) / 2, y + (row_h - 8) / 2 - 14), premium, font=f_row_value, fill=GREEN)

    y += row_h

# Footer
footer = "MANY MORE FEATURES YOU WILL SEE WHILE PLAYING THE GAME!"
fb = draw.textbbox((0, 0), footer, font=f_footer)
fw = fb[2] - fb[0]
draw.line([(120, y + 15), (W - 120, y + 15)], fill=PINK_BORDER, width=2)
draw.text(((W - fw) / 2, y + 35), footer, font=f_footer, fill=(220, 190, 255))

img = img.filter(ImageFilter.SMOOTH_MORE)
img.save("/home/claude/bts_bot/assets/premium_features.png", "PNG")
print("saved", img.size)
