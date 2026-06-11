import logging
import os
from datetime import datetime

def setup_logger(per_session=True):
    log_dir = r"E:\Programming Workspace\Python\BA-Sauerteig\log"
    os.makedirs(log_dir, exist_ok=True)

    if per_session:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"session_{timestamp}.log")
    else:
        tag = datetime.now().strftime("%Y%m%d")
        log_file = os.path.join(log_dir, f"log_{tag}.log")

    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M",
    )
    return logging.getLogger(__name__)