import os
import re
import time
import sys
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator  # có thể thay bằng DeepL API

# ===================== Cấu hình =====================
translator = GoogleTranslator(source="en", target="vi")
game_folder = r"D:/Game/Visua_novel/I_Am_Motherfucker/I Am Motherfucker/game"
tl_folder = os.path.join(game_folder, "tl", "vietnamese")
os.makedirs(tl_folder, exist_ok=True)

# Cache để tránh dịch lại
translation_cache = {}

# Regex giữ nguyên placeholder {variable}
placeholder_pattern = re.compile(r"\{.*?\}")

# ===================== Chia đoạn =====================
def split_into_paragraphs(lines, max_len=500):
    paragraphs = []
    buffer = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                paragraphs.append(buffer)
                buffer = ""
        else:
            if len(buffer) + len(stripped) + 1 > max_len:
                paragraphs.append(buffer)
                buffer = stripped
            else:
                buffer += " " + stripped if buffer else stripped
    if buffer:
        paragraphs.append(buffer)
    return paragraphs

# ===================== Dịch an toàn =====================
def safe_translate(text, retries=3, delay=2):
    if not text.strip():
        return text
    if text in translation_cache:
        return translation_cache[text]
    
    # giữ placeholder
    placeholders = placeholder_pattern.findall(text)
    text_for_translation = placeholder_pattern.sub("<PLACEHOLDER>", text)
    
    for i in range(retries):
        try:
            translated = translator.translate(text_for_translation)
            # thay lại placeholder
            for ph in placeholders:
                translated = translated.replace("<PLACEHOLDER>", ph, 1)
            translation_cache[text] = translated
            return translated
        except Exception as e:
            time.sleep(delay * (i + 1))
    translation_cache[text] = text
    return text  # fallback giữ nguyên

# ===================== Dịch 1 file =====================
def translate_file(file_name, progress_dict, index):
    input_path = os.path.join(game_folder, file_name)
    output_path = os.path.join(tl_folder, file_name)

    with open(input_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    paragraphs = split_into_paragraphs(lines)
    total = len(paragraphs)
    translated_paragraphs = []

    for i, p in enumerate(paragraphs):
        translated_paragraphs.append(safe_translate(p))
        progress_dict[index] = (i + 1) / total * 100

    # Ghi lại file, thay thế từng đoạn
    output_lines = []
    para_idx = 0
    buffer = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
                # thay buffer bằng bản dịch
                output_lines.extend(translated_paragraphs[para_idx].splitlines(keepends=True))
                para_idx += 1
                buffer = ""
            output_lines.append(line)
        else:
            buffer += line
    if buffer:
        output_lines.extend(translated_paragraphs[para_idx].splitlines(keepends=True))

    with open(output_path, "w", encoding="utf-8") as f:
        f.writelines(output_lines)

    progress_dict[index] = 100
    return file_name

# ===================== Danh sách file .rpy =====================
rpy_files = [f for f in os.listdir(game_folder) if f.endswith(".rpy")]
progress_dict = {i: 0 for i in range(len(rpy_files))}

# ===================== In tiến trình =====================
def print_progress():
    for idx, f in enumerate(rpy_files):
        percent = progress_dict[idx]
        sys.stdout.write(f"[{idx+1}/{len(rpy_files)}] {f}: {percent:.1f}% hoàn thành\n")
    sys.stdout.flush()

# ===================== Dịch đa luồng =====================
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(translate_file, f, progress_dict, idx): idx for idx, f in enumerate(rpy_files)}

    while any(f.running() for f in futures):
        sys.stdout.write("\033[F" * len(rpy_files))  # di chuyển cursor lên đầu
        print_progress()
        time.sleep(0.3)

    # In lần cuối
    sys.stdout.write("\033[F" * len(rpy_files))
    print_progress()

print("\n🎉 Hoàn tất dịch tất cả file .rpy!")
