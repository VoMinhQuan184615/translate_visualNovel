import os
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from deep_translator import GoogleTranslator

# ===================== Cấu hình =====================
translator = GoogleTranslator(source="en", target="vi")
game_folder = r"D:/Game/Visua_novel/I_Am_Motherfucker/I Am Motherfucker/game"
tl_folder = os.path.join(game_folder, "tl", "vietnamese")
os.makedirs(tl_folder, exist_ok=True)

pattern = re.compile(r'\"(.*?)\"')

# ===================== Hàm chia câu dài =====================
def split_long_text(text, max_len=200):
    if len(text) <= max_len:
        return [text]
    split_points = [m.end() for m in re.finditer(r'[.,;!?]\s', text)]
    parts = []
    last = 0
    for point in split_points:
        if point - last > max_len:
            parts.append(text[last:point])
            last = point
    if last < len(text):
        parts.append(text[last:])
    return parts if parts else [text]

# ===================== Dịch an toàn =====================
def safe_translate(text, retries=3, delay=2):
    if not text.strip():
        return text
    for i in range(retries):
        try:
            translated = translator.translate(text)
            if translated is None:
                return text
            return translated
        except Exception as e:
            wait = delay * (i + 1)
            time.sleep(wait)
    return text  # fallback: giữ nguyên text gốc

# ===================== Dịch 1 file =====================
def translate_file(file_name, progress_dict, index):
    input_path = os.path.join(game_folder, file_name)
    output_path = os.path.join(tl_folder, file_name)

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Lấy tất cả text trong file
    line_indices = []
    texts_to_translate = []

    for idx, line in enumerate(lines):
        matches = pattern.findall(line)
        for m in matches:
            parts = split_long_text(m)
            for part in parts:
                texts_to_translate.append(part)
                line_indices.append((idx, part))

    total = len(texts_to_translate)
    if total == 0:
        progress_dict[index] = 100
        return file_name

    # Dịch từng câu và cập nhật tiến trình
    translated_texts = []
    for i, t in enumerate(texts_to_translate):
        translated_texts.append(safe_translate(t))
        progress_dict[index] = (i + 1) / total * 100

    # Thay text vào file
    for (idx, original), translated in zip(line_indices, translated_texts):
        lines[idx] = lines[idx].replace(original, translated)

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    progress_dict[index] = 100
    return file_name

# ===================== Danh sách file .rpy =====================
rpy_files = [f for f in os.listdir(game_folder) if f.endswith(".rpy")]
progress_dict = {i:0 for i in range(len(rpy_files))}

# ===================== Hàm in tiến trình =====================
def print_progress():
    for idx, f in enumerate(rpy_files):
        sys.stdout.write(f"\r\033[{len(rpy_files)}A")  # move cursor up
        break
    for idx, f in enumerate(rpy_files):
        percent = progress_dict[idx]
        sys.stdout.write(f"[{idx+1}/{len(rpy_files)}] {f}: {percent:.1f}% câu hoàn thành\n")
    sys.stdout.flush()

# ===================== Dịch đa luồng =====================
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(translate_file, f, progress_dict, idx): idx for idx, f in enumerate(rpy_files)}

    # Cập nhật tiến trình liên tục
    while any(future.running() for future in futures):
        print_progress()
        time.sleep(0.2)

    # In lần cuối sau khi tất cả xong
    print_progress()

print("\n🎉 Hoàn tất dịch tất cả file .rpy!")
