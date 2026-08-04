import datetime
import logging
import shutil
import subprocess
from pathlib import Path


class BackupGitPusher:
    def __init__(self, repo_url, git_user, git_token, backup_dir, retention_days=7):
        self.repo_url = repo_url
        self.git_user = git_user
        self.git_token = git_token
        self.backup_dir = Path(backup_dir)
        self.retention_days = retention_days
        self.workdir = Path("/repo")
        self.logger = logging.getLogger(__name__)

    def _run(self, cwd, *args):
        return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True)

    def _auth_url(self):
        return self.repo_url.replace(
            "https://", f"https://{self.git_user}:{self.git_token}@"
        )

    def push(self, filepath):
        if self.workdir.exists():
            shutil.rmtree(self.workdir)

        result = self._run(
            None,
            "git",
            "clone",
            "--quiet",
            "--depth",
            "1",
            self._auth_url(),
            str(self.workdir),
        )
        if result.returncode != 0:
            self.logger.error("Falha ao clonar repo de backups: %s", result.stderr)
            raise RuntimeError("Falha ao clonar repo de backups")

        shutil.copy(filepath, self.workdir / filepath.name)

        self._run(self.workdir, "git", "config", "user.email", "backup@postgres.local")
        self._run(self.workdir, "git", "config", "user.name", "Postgres Backup")
        self._run(self.workdir, "git", "add", filepath.name)

        commit = self._run(
            self.workdir,
            "git",
            "commit",
            "-m",
            f"backup {self._now()}: {filepath.name}",
        )
        if commit.returncode == 0:
            push = self._run(self.workdir, "git", "push", "origin", "HEAD")
            if push.returncode != 0:
                self.logger.error("Falha no push do backup: %s", push.stderr)
                raise RuntimeError("Falha no push do backup")
            self.logger.info("Backup enviado para o repo: %s", filepath.name)
        else:
            self.logger.info("Nenhuma mudanca para commitar")

        self._run(self.workdir, "git", "remote", "set-url", "origin", self.repo_url)
        self._cleanup_old()

    def _now(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _cleanup_old(self):
        cutoff = datetime.datetime.now() - datetime.timedelta(days=self.retention_days)
        for f in self.backup_dir.glob("*.sql"):
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                f.unlink()
                self.logger.info("Backup antigo removido: %s", f.name)
