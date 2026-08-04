import datetime
import json
import logging

import pika


class RabbitNotifier:
    def __init__(self, host, port, username, password, queue, email=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.queue = queue
        self.email = email
        self.logger = logging.getLogger(__name__)

    def notify(self, status, database, filename=None, message=None):
        credentials = pika.PlainCredentials(self.username, self.password)
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host, port=self.port, credentials=credentials, heartbeat=600
            )
        )
        channel = connection.channel()
        channel.queue_declare(queue=self.queue, durable=True)

        body = {
            "app": "backup-postgres-service",
            "status": status,
            "database": database,
            "timestamp": datetime.datetime.now().isoformat(),
            "filename": filename,
            "message": message,
            "email": self.email,
        }

        channel.basic_publish(
            exchange="",
            routing_key=self.queue,
            body=json.dumps(body, ensure_ascii=False),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
                priority=0,
            ),
        )
        connection.close()
        self.logger.info("Notificacao enviada para %s: %s", self.queue, status)
