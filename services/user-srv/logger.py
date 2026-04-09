import logging

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_logger(name: str = "") -> logging.Logger:
    name = f"user-srv.{name}" if name else "user-srv"
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger
