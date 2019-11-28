import logging
import sys

#logging.basicConfig(
#    level=logging.DEBUG,
#    format=logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
#)

def get_aim_logger():
    log = logging.getLogger("aim")
    log.setLevel(logging.DEBUG) 
    return log

# Logging 101:
# logging.getLogger("aim").debug("Logging has been configured.")
# logger.debug
# logger.info
# logger.warn
# logger.error
# logger.critical
