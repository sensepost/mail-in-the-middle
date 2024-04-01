#/usr/bin/env python

from Maitm.Maitm import Maitm
import logging.config
import argparse
from datetime import datetime
import os
import yaml

############
# FUNCTION #
############

def init_logging(log_filename):
    # Ensure the 'logs' directory exists
    os.makedirs(os.path.dirname(log_filename), exist_ok=True)

    # Load the logging configuration from a YAML file
    with open('config/logging.yml', 'r') as f:
        config = yaml.safe_load(f.read())
        # Update the filename in the configuration
        config['handlers']['file_handler']['filename'] = log_filename
        logging.config.dictConfig(config)

    # Example usage
    logger = logging.getLogger()
    logger.info("Init logging finished")
    return logger

def parse_arguments():
    parser = argparse.ArgumentParser(description='Monitor and relay emails with typos')
    parser.add_argument('-c','--config', dest='config',
                        help='Configuration file with IMAP and SMTP details (Default: config/config.yml)', default="config/config.yml")
    parser.add_argument('-n','--new', dest='new', action="store_true",
                        help='Poll only for new emails')
    parser.add_argument('-f','--forward', dest='forward', action="store_true", default=False,
                        help='Forward the emails automatically (default: False)')

    return parser.parse_args()

########
# MAIN #
########

def main():
    # Parse options
    arguments=parse_arguments()
    # Init logging
    log_filename = "logs/" + datetime.now().strftime('%Y%m%d_%H%M%S') + '_mailinthemiddle.log'
    init_logging(log_filename)
    # Create forwarded emails list file if it does not exists
    if not os.path.exists("forwardedemails.txt"):
        open("forwardedemails.txt", "w").close()

    # Create Maitm object
    maitm = Maitm(config_file=arguments.config, 
                  only_new=arguments.new,
                  forward_emails=arguments.forward,
                  logfile=log_filename)
    logging.info("Logging to SMTP server")
    maitm.smtp_login()
    logging.info("Logging to IMAP server")
    maitm.imap_login()

    # Initial Heartbeat
    # maitm.heartbeat()
    logging.info("Monitoring inbox now...")
    maitm.monitor_inbox()

if __name__ == "__main__":
    main()