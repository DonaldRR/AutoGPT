import colorlog

handler = colorlog.StreamHandler()
handler.setFormatter(
    colorlog.ColoredFormatter(
        '%(log_color)s%(levelname)s:%(message)s',
        log_colors={
            'DEBUG': 'green',
            'INFO': 'blue',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'reg,bg_white',
        }
    )
)

def color_logger(logger):
    logger.addHandler(handler)