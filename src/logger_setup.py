import logging
from datetime import datetime

def log(logger: logging.Logger, msg: str):
    # log einträge können auch im code sein, owbohl nicht geloggt werden soll
    if logger:
        logger.info(msg)

def setup_logger(log_dir: Path, per_session: bool = True, file_name: str | None = None) -> logging.Logger:
    """Konfiguriert den Logger und initialisiert ihn. Kann für Batchläufe eine Datei schreiben und für Einzeldurchläufe mehrere. 

    Args:
        log_dir (Path): Ablagepfad
        per_session (bool, optional): Batch- oder Einzelauswahl. Defaults to True.
        file_name (str | None, optional): Dateiname. Defaults to None.

    Returns:
        Logger: der angelegte Log
    """
    if not file_name:
        if per_session:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            log_file = log_dir / f"session_{timestamp}.log"
        else:
            tag = datetime.now().strftime("%Y%m%d")
            log_file = log_dir / f"log_{tag}.log"
    else:
        if per_session:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            log_file = log_dir / f"{file_name}_{timestamp}.log"
        else:
            tag = datetime.now().strftime("%Y%m%d")
            log_file = log_dir / f"{file_name}_{tag}.log"
    logging.basicConfig(filename=log_file, encoding='utf-8', level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M")
    return logging.getLogger(__name__)