import logging
import os

HOSTNAME = os.getenv("HOSTNAME")

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_logger(name: str = "") -> logging.Logger:
    prefix = f"notification-srv[{HOSTNAME}]"
    name = f"{prefix}.{name}" if name else prefix
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
