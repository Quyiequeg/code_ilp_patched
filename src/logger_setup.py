import logging
from datetime import datetime

def log(logger: logging.Logger, msg: str):
    if logger:
        logger.info(msg)

def setup_logger(log_dir, per_session=True):
    if per_session:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        log_file = log_dir / f"session_{timestamp}.log"
    else:
        tag = datetime.now().strftime("%Y%m%d")
        log_file = log_dir / f"log_{tag}.log"

    logging.basicConfig(filename=log_file, encoding='utf-8', level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M")
    return logging.getLogger(__name__)