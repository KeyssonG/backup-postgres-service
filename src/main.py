import logging
import os
import time

import schedule

from backup import PostgreSQLBackup
from git_push import BackupGitPusher
from rabbit_notifier import RabbitNotifier


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    logger = logging.getLogger(__name__)

    databases = [
        d.strip()
        for d in os.environ.get("BACKUP_DATABASES", os.environ["DB_NAME"]).split(",")
        if d.strip()
    ]

    pusher = BackupGitPusher(
        repo_url=os.environ["BACKUP_REPO_URL"],
        git_user=os.environ["GIT_USER"],
        git_token=os.environ["GIT_TOKEN"],
        backup_dir="/backups",
        retention_days=int(os.environ.get("BACKUP_RETENTION_DAYS", "7")),
    )

    notifier = RabbitNotifier(
        host=os.environ.get("HOST_RABBIT", "rabbitmq"),
        port=int(os.environ.get("PORT_RABBIT", "5672")),
        username=os.environ.get("USER_RABBIT", "admin"),
        password=os.environ.get("PASSWORD_RABBIT", ""),
        queue=os.environ.get("BACKUP_QUEUE", "backup.fila"),
        email=os.environ.get("EMAIL_TO", ""),
    )

    def backup_database(database):
        backup = PostgreSQLBackup(
            host=os.environ["DB_HOST"],
            port=os.environ.get("DB_PORT", "5432"),
            database=database,
            username=os.environ["DB_USER"],
            password=os.environ.get("DB_PASSWORD", ""),
        )
        filepath = backup.create_backup()
        if filepath:
            pusher.push(filepath)
            notifier.notify(
                status="success",
                database=database,
                filename=filepath.name,
                message=f"Backup {filepath.name} enviado para o repositorio",
            )
        else:
            notifier.notify(
                status="error",
                database=database,
                message="Falha ao gerar pg_dump",
            )

    def job():
        for database in databases:
            try:
                backup_database(database)
            except Exception as e:
                logger.exception("Falha no ciclo de backup do banco %s", database)
                notifier.notify(status="error", database=database, message=str(e))

    interval = int(os.environ.get("BACKUP_INTERVAL_MINUTES", "60"))
    logger.info("Bancos configurados: %s", ", ".join(databases))
    logger.info("Executando backup imediato na inicializacao")
    job()

    schedule.every(interval).minutes.do(job)
    logger.info("Backup agendado a cada %s minutos", interval)

    while True:
        schedule.run_pending()
        time.sleep(10)


if __name__ == "__main__":
    main()
