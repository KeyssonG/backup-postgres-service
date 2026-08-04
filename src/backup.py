import datetime
import logging
import os
import subprocess
from pathlib import Path


class PostgreSQLBackup:
    def __init__(self, host, port, database, username, password):
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self.backup_dir = Path("/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def create_backup(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{self.database}_backup_{timestamp}.sql"

        cmd = [
            "pg_dump",
            f"--host={self.host}",
            f"--port={self.port}",
            f"--username={self.username}",
            "--no-password",
            "--clean",
            "--no-owner",
            "--no-privileges",
            f"--file={backup_path}",
            self.database,
        ]

        env = os.environ.copy()
        env["PGPASSWORD"] = self.password

        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            self.logger.error("pg_dump falhou para o banco '%s': %s", self.database, result.stderr)
            return None

        self.logger.info(
            "Backup criado: %s (%s bytes)", backup_path.name, backup_path.stat().st_size
        )
        return backup_path
