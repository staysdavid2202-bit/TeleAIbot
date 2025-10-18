import os
import shutil

# Путь, где нужно удалить все папки
base_path = "."

# 1️⃣ Удаляем все папки
for name in os.listdir(base_path):
    full_path = os.path.join(base_path, name)
    if os.path.isdir(full_path):
        shutil.rmtree(full_path)
        print(f"Удалена папка: {full_path}")

# 2️⃣ Создаём новые папки
folders_to_create = ["data", "logs", "cache"]
for folder in folders_to_create:
    os.makedirs(os.path.join(base_path, folder), exist_ok=True)
    print(f"Создана папка: {folder}")
