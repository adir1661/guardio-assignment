import logging


class ModuleNameFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        formatted_str = super().format(record)
        return f"({record.name}):{record.levelname} - {formatted_str}"
