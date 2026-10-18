import os
import shutil
import datetime

# Paths (project root assumed to be where this script lives)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'database.db')
KEY_DIR = os.path.join(BASE_DIR, 'keys')
BACKUP_ROOT = os.path.join(BASE_DIR, 'backups')

def ensure_backup_dir():
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = os.path.join(BACKUP_ROOT, f'backup_{timestamp}')
    os.makedirs(backup_dir, exist_ok=True)
    return backup_dir

def backup_file(src_path, dest_dir):
    if os.path.isfile(src_path):
        shutil.copy2(src_path, dest_dir)
        print(f"Backed up {os.path.basename(src_path)}")
    else:
        print(f"File not found, skipping: {src_path}")

def backup_directory(src_dir, dest_dir):
    if os.path.isdir(src_dir):
        dest_sub = os.path.join(dest_dir, os.path.basename(src_dir))
        shutil.copytree(src_dir, dest_sub)
        print(f"Backed up directory {src_dir} -> {dest_sub}")
    else:
        print(f"Directory not found, skipping: {src_dir}")

def main():
    backup_dir = ensure_backup_dir()
    # Backup SQLite DB
    backup_file(DB_PATH, backup_dir)
    # Backup keys (private and public)
    backup_directory(KEY_DIR, backup_dir)
    # Optionally backup config files (if any)
    config_files = ['config.py']
    for cfg in config_files:
        backup_file(os.path.join(BASE_DIR, cfg), backup_dir)
    print(f"Backup completed at {backup_dir}")

if __name__ == '__main__':
    main()
