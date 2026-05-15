"""Fábrica de loggers compartilhada do projeto."""

import json
import logging
from pathlib import Path


class _JsonLineFormatter(logging.Formatter):
    """Formata cada registro como uma linha JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for campo in ("ano", "trimestre", "status", "origem", "erro"):
            if hasattr(record, campo):
                payload[campo] = getattr(record, campo)
        return json.dumps(payload, ensure_ascii=False)


_FORMATTER_HUMANO = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str, log_file: Path) -> logging.Logger:
    """Retorna logger configurado com FileHandler (JSON line) e StreamHandler (texto).

    Args:
        name: Nome do logger, geralmente ``__name__`` do módulo chamador.
        log_file: Caminho absoluto ou relativo do arquivo de log. O diretório
            pai é criado automaticamente se não existir.

    Returns:
        Logger configurado e pronto para uso.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    log_file = Path(log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(_JsonLineFormatter())

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(_FORMATTER_HUMANO)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    return logger
