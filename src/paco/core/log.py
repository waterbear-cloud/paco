import logging
import sys

#logging.basicConfig(
#    level=logging.DEBUG,
#    format=logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
#)

def get_paco_logger():
    log = logging.getLogger("paco")
    log.setLevel(logging.DEBUG)
    return log

# Logging 101:
# logging.getLogger("paco").debug("Logging has been configured.")
# logger.debug
# logger.info
# logger.warn
# logger.error
# logger.critical
