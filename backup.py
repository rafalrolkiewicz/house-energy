"""
This program creates copy of database file.
"""

from datetime import datetime
import shutil
import message_sender as telegram

database_file = "electricity.db"


def make_database_backup():
    """
    Creates a backup of the database file and saves it in the
    'backup' directory. Sends a message via Telegram to notify the user
    of the backup status.
    """
    timestamp = datetime.now().strftime("%Y%m%d")
    backup_file = f"backup/electricity{timestamp}.db"
    now = datetime.now().replace(microsecond=0)
    try:
        shutil.copy2(database_file, backup_file)
        print(f"{now} Backup completed successfully!")
        telegram.send_message(f"{now} Backup completed successfully!")
    except:
        print(f"{now} Error, couldn't make database backup")
        telegram.send_message(f"{now} Error, couldn't make database backup")
