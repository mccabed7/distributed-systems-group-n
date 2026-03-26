import logging

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def get_logger(name: str = "") -> logging.Logger:
    name = f"gateway-srv.{name}" if name else "gateway-srv"
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger