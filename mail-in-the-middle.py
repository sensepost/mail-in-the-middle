#/usr/bin/env python

from Maitm import Maitm
import logging.config
import argparse
from datetime import datetime
import os
import yaml
from tui import MaitmTUI

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
    current_file_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description='Monitor and relay emails with typos')
    
    # Add a positional argument 'mode' (either 'tui' or 'cli')
    parser.add_argument('mode', choices=['tui', 'cli'], 
                        help="Mode to run the program in: 'tui' for the graphical interface, 'cli' for command-line interface")

    # Optional arguments (only for CLI mode)
    parser.add_argument('-c','--config', dest='config',
                        help='Configuration file with IMAP and SMTP details (Default: config/config.yml)', 
                        default=os.path.join(current_file_dir, "config/config.yml"))
    parser.add_argument('-n','--new', dest='new', action="store_true",
                        help='Poll only for new emails')
    parser.add_argument('-f','--forward', dest='forward', action="store_true", default=False,
                        help='Forward the emails automatically (default: False)')
    
    args = parser.parse_args()

    return args

def get_version():
    v = "vX.X.X"
    with open("version","r") as f:
        v = f.readlines()[0].strip()
    return v

# https://stackoverflow.com/questions/40419276/python-how-to-print-text-to-console-as-hyperlink
def link(uri, label=None):
    if label is None: 
        label = uri
    parameters = ''

    # OSC 8 ; params ; URI ST <name> OSC 8 ;; ST 
    escape_mask = '\033]8;{};{}\033\\{}\033]8;;\033\\'

    return escape_mask.format(parameters, uri, label)

def banner():
    b = """
███╗   ███╗ █████╗ ██╗████████╗███╗   ███╗
████╗ ████║██╔══██╗██║╚══██╔══╝████╗ ████║
██╔████╔██║███████║██║   ██║   ██╔████╔██║
██║╚██╔╝██║██╔══██║██║   ██║   ██║╚██╔╝██║
██║ ╚═╝ ██║██║  ██║██║   ██║   ██║ ╚═╝ ██║
╚═╝     ╚═╝╚═╝  ╚═╝╚═╝   ╚═╝   ╚═╝     ╚═╝  %s

Man in the Middle, but for Mails

"""
    b2 = f"Author: Felipe Molina de la Torre ({link('https://x.com/felmoltor',label='@felmoltor')})"
    b3 = f"Original idea: Willem Mouton ({link('https://x.com/_w_m__',label='@_w_m__')}), continued by Szymon Zilokowski ({link('https://x.com/TH3_GOAT_FARM3R',label='@TH3_GOAT_FARM3R')})"
    print(b % get_version() + b2 + "\n" + b3 + "\n")

########
# MAIN #
########

def main():
    banner()
    # Parse options
    arguments=parse_arguments()    

    # Check if the config path is relative
    if not os.path.isabs(arguments.config):
        # If it is, convert it to an absolute path using the current working directory
        arguments.config = os.path.join(os.getcwd(), arguments.config)

    # Init logging
    log_filename = "logs/" + datetime.now().strftime('%Y%m%d_%H%M%S') + '_mailinthemiddle.log'
    init_logging(log_filename)
    # Create forwarded emails list file if it does not exists
    if not os.path.exists("forwardedemails.txt"):
        open("forwardedemails.txt", "w").close()

    if arguments.mode == 'tui':
        # Start the GUI application
        app = MaitmTUI()  # Assuming MaitmTUI is your Textual GUI class
        app.run()
    else:
        # Run the CLI version of the tool
        print(f"Running in CLI mode with config: {arguments.config}")
        # Create Maitm object
        maitm = Maitm(config_file=arguments.config, 
                    only_new=arguments.new,
                    forward_emails=arguments.forward,
                    logfile=log_filename)
        logging.info("[%s] Logging to server for reading emails" % maitm.mailmanager.read_protocol.value)
        maitm.mailmanager.login_read()
        logging.info("[%s] Logging to server for sending emails" % maitm.mailmanager.send_protocol.value)
        maitm.mailmanager.login_send()

        # Initial Heartbeat
        # maitm.heartbeat()
        logging.info("Monitoring inbox now...")
        maitm.monitor_inbox()

if __name__ == "__main__":
    main()
