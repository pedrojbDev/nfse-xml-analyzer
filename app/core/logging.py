import logging

def setup_logging() -> logging.Logger:
    logger = logging.getLogger("doc_api")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    return logger
