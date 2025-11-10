import os
import re
import time
import sys
import argparse
from concurrent.futures import ThreadPoolExecutor
from deep_translator import GoogleTranslator

# ===================== Nhận đường dẫn từ CMD =====================
parser = argparse.ArgumentParser(description="Dịch .rpy sang tiếng Việt")
parser.add_argument("--game_folder", type=str, required=True, help="Đường dẫn folder game chứa file .rpy")
args = parser.parse_args()

game_folder = os.path.abspath(args.game_folder)
tl_folder = os.path.join(game_folder, "tl", "vietnamese")
os.makedirs(tl_folder, exist_ok=True)

# ===================== Cấu hình dịch =====================
translator = GoogleTranslator(source="en", target="vi")
translation_cache = {}
placeholder_pattern = re.compile(r"\{.*?\}")

# ===================== Hàm chia đoạn =====================
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
    placeholders = placeholder_pattern.findall(text)
    text_for_translation = placeholder_pattern.sub("<PLACEHOLDER>", text)
    for i in range(retries):
        try:
            translated = translator.translate(text_for_translation)
            for ph in placeholders:
                translated = translated.replace("<PLACEHOLDER>", ph, 1)
            translation_cache[text] = translated
            return translated
        except Exception:
            time.sleep(delay * (i + 1))
    translation_cache[text] = text
    return text

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

    output_lines = []
    para_idx = 0
    buffer = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buffer:
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

    sys.stdout.write("\033[F" * len(rpy_files))
    print_progress()

print("\n🎉 Hoàn tất dịch tất cả file .rpy!")
