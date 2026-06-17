from PIL import Image, ImageDraw, ImageFont
import os, uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_BOLD = os.path.join(BASE_DIR, "Montserrat-Bold.ttf")
FONT_SEMI = os.path.join(BASE_DIR, "Montserrat-SemiBold.ttf")
FONT_REG  = os.path.join(BASE_DIR, "Montserrat-Regular.ttf")
QR_TG     = os.path.join(BASE_DIR, "qr_telegram.jpg")
QR_VK     = os.path.join(BASE_DIR, "qr_vk.jpg")
OWL       = os.path.join(BASE_DIR, "owl_transparent.png")

C_BG       = (252, 246, 250)
C_HEADER   = (220, 35, 105)
C_WHITE    = (255, 255, 255)
C_CARD     = (255, 255, 255)
C_NAVY     = (18, 24, 68)
C_GRAY     = (140, 145, 168)
C_DIVIDER  = (230, 222, 238)
C_CARD_BDR = (232, 222, 240)
C_STRIPE   = (220, 35, 105)
C_NUM_BG   = (235, 228, 255)
C_NUM_TEXT = (72, 40, 160)


def generate_ticket(data: dict) -> str:
    W, H      = 960, 520
    HEADER_H  = 130
    BLOCK_X2  = 590

    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    f_sublabel = ImageFont.truetype(FONT_SEMI, 16)
    f_brand    = ImageFont.truetype(FONT_BOLD, 48)
    f_love     = ImageFont.truetype(FONT_SEMI, 17)
    f_sub90    = ImageFont.truetype(FONT_SEMI, 20)
    f_num      = ImageFont.truetype(FONT_BOLD, 50)
    f_numlbl   = ImageFont.truetype(FONT_SEMI, 14)
    f_label    = ImageFont.truetype(FONT_REG,  15)
    f_value    = ImageFont.truetype(FONT_SEMI, 25)
    f_small    = ImageFont.truetype(FONT_REG,  13)
    f_mini     = ImageFont.truetype(FONT_REG,  12)
    f_qrlbl    = ImageFont.truetype(FONT_SEMI, 13)

    QR           = 140
    right_zone_x = BLOCK_X2 + 14
    right_zone_w = W - 14 - right_zone_x
    QR_X         = right_zone_x + (right_zone_w - QR) // 2

    # ── Левая полоса ──
    draw.rectangle([0, 0, 7, H], fill=C_STRIPE)

    # ── Шапка ──
    draw.rectangle([0, 0, W, HEADER_H], fill=C_HEADER)

    # ── Логотип-сова слева в шапке ──
    OWL_H = 124   # высота совы = высота шапки
    if os.path.exists(OWL):
        owl = Image.open(OWL).convert("RGBA")
        # Сова квадратная 2048×2048 — масштабируем по высоте
        owl = owl.resize((OWL_H, OWL_H), Image.LANCZOS)
        # Вставляем с учётом прозрачности
        img.paste(owl, (8, 3), owl)

    # Текст в шапке — сдвинут правее совы
    TX = OWL_H + 16   # X начала текста
    draw.text((TX, 8),  "Музыкальная лотерея", font=f_sublabel, fill=(255, 200, 225))
    draw.text((TX, 30), "3а3о",                font=f_brand,    fill=C_WHITE)
    draw.text((TX, 82), "Выиграй любовь  ·  Назад в 90-е", font=f_sub90, fill=(255, 200, 225))

    # ── Бейдж номера — справа в шапке ──
    BW, BH = 210, 106
    BX = W - BW - 16
    draw.rounded_rectangle([BX, 12, BX+BW, 12+BH], radius=12, fill=C_NUM_BG)
    draw.text((BX+14, 20),  "БИЛЕТ",                   font=f_numlbl, fill=C_NUM_TEXT)
    draw.text((BX+10, 38),  f"№ {data['number']:03d}", font=f_num,    fill=C_NUM_TEXT)

    # ── Строка события ──
    draw.text((20, HEADER_H + 8),
              "25 июня 2026  ·  сбор 18:00, старт 18:30  ·  Ресторан «Золотой телец», Кузнецк",
              font=f_small, fill=C_GRAY)

    # ── Белый блок данных ──
    BLOCK_Y1 = HEADER_H + 30
    BLOCK_Y2 = H - 26
    draw.rounded_rectangle([16, BLOCK_Y1, BLOCK_X2, BLOCK_Y2],
                            radius=12, fill=C_CARD,
                            outline=C_CARD_BDR, width=1)

    # ── 4 поля гостя ──
    LX  = 34
    TOP = BLOCK_Y1 + 16
    fields = [
        ("ГОСТЬ",    data["фио"]),
        ("МЕСТ",     str(data["места"])),
        ("ОПЛАЧЕНО", f"{data['сумма']:,} ₽".replace(",", " ")),
        ("КОНТАКТ",  data["контакт"]),
    ]
    for i, (label, value) in enumerate(fields):
        y = TOP + i * 78
        draw.text((LX, y),      label, font=f_label, fill=C_GRAY)
        draw.text((LX, y + 20), value, font=f_value, fill=C_NAVY)
        if i < len(fields) - 1:
            draw.rectangle([LX, y + 56, BLOCK_X2 - 16, y + 57], fill=C_DIVIDER)

    # ── Дата — правый нижний угол блока ──
    ts_w = draw.textlength(data["timestamp"], font=f_mini)
    draw.text((BLOCK_X2 - ts_w - 14, BLOCK_Y2 - 18),
              data["timestamp"], font=f_mini, fill=C_GRAY)

    # ── QR-коды — вертикально, центр правой зоны ──
    block_h  = BLOCK_Y2 - BLOCK_Y1
    label_h  = 20
    gap      = 14
    total_qr = QR * 2 + label_h * 2 + gap
    QR_Y1    = BLOCK_Y1 + (block_h - total_qr) // 2
    QR_Y2    = QR_Y1 + QR + label_h + gap

    for fpath, y, label in [(QR_TG, QR_Y1, "Telegram"),
                             (QR_VK, QR_Y2, "ВКонтакте")]:
        if os.path.exists(fpath):
            draw.rounded_rectangle(
                [QR_X - 6, y - 6, QR_X + QR + 6, y + QR + 6],
                radius=8, fill=C_CARD, outline=C_CARD_BDR, width=1
            )
            qr = Image.open(fpath).convert("RGB").resize((QR, QR))
            img.paste(qr, (QR_X, y))
            lw = draw.textlength(label, font=f_qrlbl)
            draw.text((QR_X + (QR - lw) // 2, y + QR + 5),
                      label, font=f_qrlbl, fill=C_GRAY)

    hint_y = QR_Y2 + QR + label_h + 4
    if hint_y + 28 < BLOCK_Y2:
        for j, txt in enumerate(["По вопросам:", "свяжитесь с нами"]):
            tw = draw.textlength(txt, font=f_mini)
            draw.text((QR_X + (QR - tw) // 2, hint_y + j * 14),
                      txt, font=f_mini, fill=C_GRAY)

    # ── Нижняя полоса ──
    draw.rectangle([0, H-6, W, H], fill=C_STRIPE)

    tmp = os.path.join(BASE_DIR, f"ticket_{uuid.uuid4().hex[:8]}.png")
    img.save(tmp, "PNG")
    return tmp
