# General imports
import yaml
from enum import Enum
import logging.config
import os
from datetime import datetime, timedelta
import base64
# Mail imports 
from exchangelib import Configuration, OAuth2LegacyCredentials, OAuth2Credentials, Credentials, Account, DELEGATE, Message as ExchangeMessage, Mailbox as ExchangeMailbox,Q, EWSDateTime, OAUTH2
from smtplib import SMTP
from imap_tools import MailBox as ImapMailBox, AND, OR
from email import message_from_string
from email.message import EmailMessage as PythonEmailMessage
from .MailConverter import MailConverter

"""
This enum class is used to define the supported mail protocols
"""
class MailProtocols(Enum):
    SMTP = "smtp"
    EWS = "ews"
    IMAP = "imap"
    OAUTH2 = "oauth2"
    OAUTH2LEGACY = "oauth2legacy"

"""
This class is in charge of reading and sending out emails to the users:
* The reading and sending functionality will be implemented to abastract the email reading and sending process to Maitm
* The reading should support imap and ews protocols
* The sending should support smtp and ews protocols
* The class reads the configuration from the file config/auth.yml and allows Maitm to do the following
 1. Read N emails from the user's email account with the following filters: reception date, sender, subject
 2. Send emails to a user's email account
"""
class MailManager():
    def __init__(self, auth_config=None, logfile="logs/mailmanager.log"):
        self.init_logging(log_filename=logfile)
        self.config = auth_config
        self.read_protocol = None
        self.send_protocol = None
        self.read_ews_account: Account = None       # EWS account for reading emails
        self.read_oauth2_account: Account = None    # Oauth2 account for reading emails
        self.read_imap_mailbox: ImapMailBox = None      # IMAP MailBox object for reading emails
        self.send_ews_account: Account = None       # EWS account for sending emails
        self.send_oauth2_account: Account = None    # Oauth account for sending emails
        self.send_smtp_connection: SMTP = None      # SMTP connection for sending emails
        self._setup_mail_protocol()     # Populate the variables to see what protocol we are using for the email sending and reading
        self.mailconverter: MailConverter = MailConverter(logfile=datetime.now().strftime("logs/%Y%m%d_%H%M%S_mailmanager.log"))

    def init_logging(self,log_filename):
        # Ensure the 'logs' directory exists
        os.makedirs(os.path.dirname(log_filename), exist_ok=True)

        # Load the logging configuration from a YAML file
        with open('config/logging.yml', 'r') as f:
            config = yaml.safe_load(f.read())
            # Update the filename in the configuration
            config['handlers']['file_handler']['filename'] = log_filename
            logging.config.dictConfig(config)

        # Example usage
        self.logger = logging.getLogger()

    """
    This function sets up the mail protocol for reading and sending emails
    """
    def _setup_mail_protocol(self):
        rp = list(self.config['read'].keys())[0]
        sp = list(self.config['send'].keys())[0]
        try:
            self.read_protocol = MailProtocols[rp.upper()]
        except KeyError:
            raise ValueError(f"Unsupported protocol type: {rp}")
        try:
            self.send_protocol = MailProtocols[sp.upper()]
        except KeyError:
            raise ValueError(f"Unsupported protocol type: {sp}")


    ##########################
    # LOGIN EMAILS FUNCTIONS #
    ##########################

    """
    This function logs into the email server to read emails
    """
    def login_read(self):
        if (self.read_protocol == MailProtocols.EWS):
            self.read_ews_account = self._login_ews(config=self.config["read"]["ews"])
        elif (self.read_protocol == MailProtocols.OAUTH2LEGACY):
            self.read_oauth2_account = self._login_oauth2legacy(config=self.config["read"]["oauth2legacy"])
        elif (self.read_protocol == MailProtocols.OAUTH2):
            self.read_oauth2_account = self._login_oauth2(config=self.config["read"]["oauth2"])
        elif (self.read_protocol == MailProtocols.IMAP):
            self.read_imap_mailbox = self._login_imap(config=self.config["read"]["imap"])
        else:
            self.logger.error("Unsupported protocol for reading emails")

    """
    This function logs into the EWS server and returns the EWS account object for sending emails
    """
    def login_send(self):
        if (self.send_protocol == MailProtocols.EWS):
            self.send_ews_account = self._login_ews(config=self.config["send"]["ews"])
        elif (self.send_protocol == MailProtocols.OAUTH2LEGACY):
            self.send_oauth2_account = self._login_oauth2legacy(config=self.config["send"]["oauth2legacy"])
        elif (self.send_protocol == MailProtocols.OAUTH2):
            self.send_oauth2_account = self._login_oauth2(config=self.config["send"]["oauth2"])
        elif (self.send_protocol == MailProtocols.SMTP):
            self.send_smtp_connection = self._login_smpt(config=self.config["send"]["smtp"])
        else:
            self.logger.error("Unsupported protocol for reading emails")

    """
    This function logs into the EWS server and returns the Exchangelib account object
    """
    def _login_ews(self,config):
        credentials = Credentials(username=config['email'], password=config['password'])
        # Create a Configuration object
        # AutodiscoverProtocol.credentials = credentials
        mail_config = Configuration(server='outlook.office365.com', credentials=credentials)
        # Create an account instance
        account = Account(primary_smtp_address=config['email'], autodiscover=True, access_type=DELEGATE)
        # Fetch the inbox folder
        return account
    
    """
    This function logs into the EWS server using OAuth2 and returns the Exchangelib account object
    """
    def _login_oauth2(self, config):
        credentials = OAuth2Credentials(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            tenant_id=config["tenant_id"]
        )

        # Set up configuration with OAuth credentials
        configuration = Configuration(server='outlook.office365.com', credentials=credentials, auth_type=OAUTH2)

        # Initialize the account with autodiscover
        account = Account(
            primary_smtp_address=config["email"],
            config=configuration,
            autodiscover=True,
            access_type=DELEGATE
        )
        return account

    """
    This function logs into the EWS server using legacy OAuth2 and returns the Exchangelib account object
    """
    def _login_oauth2legacy(self, config):
        credentials = OAuth2LegacyCredentials(
            client_id=config["client_id"],
            client_secret=config["client_secret"],
            tenant_id=config["tenant_id"],
            password=config["password"],
            username=config["email"]
        )

        # Set up configuration with OAuth credentials
        configuration = Configuration(server='outlook.office365.com', credentials=credentials)

        # Initialize the account with autodiscover
        account = Account(
            primary_smtp_address=config["email"],
            config=configuration,
            autodiscover=True,
            access_type=DELEGATE
        )
        return account

    """
    This function logs into the SMTP server and returns the SMTP connection object
    """
    def _login_smpt(self,config):
        smtp = SMTP(config["server"], config["port"])
        smtp.ehlo()
        if (config["tls"]):
            smtp.starttls()
        # Login only if we have specified user credentials
        if (config["username"] is not None):
            smtp.login(config["username"],config["password"])
        
        return smtp

    """
    This function logs into the IMAP server and returns the mailbox object
    """
    def _login_imap(self,config):
        return ImapMailBox(config["server"],config["port"]).login(config["username"],config["password"])


    #############################
    # FETCHING EMAILS FUNCTIONS #
    #############################
    """
    This function fetches emails from the user's email account.
    It abstracts the reading process to allow Maitm to read emails using different protocols (EWS or IMAP)
    Params:
    * date_limit: retrieve emails after this date
    * domain_to: filter emails sent to this domain
    * domain_from: filter emails sent from this domain
    * subject: filter emails containing this string in the subject
    * number: number of emails to fetch
    """
    def fetch_emails(self, criteria, number: int = 10, offset: int = 0):
        if (self.read_protocol == MailProtocols.EWS or self.read_protocol == MailProtocols.OAUTH2 or self.read_protocol == MailProtocols.OAUTH2LEGACY):
            return self._fetch_emails_exchangelib(criteria, number=number)
        elif (self.read_protocol == MailProtocols.IMAP):
            return self._fetch_emails_imap(criteria, number=number)
        else:
            self.logger.error("Unsupported protocol for reading emails")
            return None

    """
    Fetches emails using the exchangelib account object
    """
    def _fetch_emails_exchangelib(self, criteria: dict, number: int = 10):
        # date_limit: datetime = None, domain_to: str = None, domain_from: str = None, subject: str = None, ignore_seen: bool=True
        self.logger.info("[Exchangelib] Fetching %s emails with criteria: %s" % (number, criteria))
        
        query = None
        if criteria["ignore_seen"]:
            query = Q(is_read=False)
        if criteria["from_date"]:
            query = query & Q(datetime_received__gt=EWSDateTime(criteria["from_date"]))
        if criteria["to_domains"]:
            query = query & criteria["to_domains"]
        if criteria["from_domains"]:
            query = query & criteria["from_domains"]
        if criteria["subject"]:
            query = query & Q(subject__contains=criteria["subject"])
        
        python_messages = list() # To store the messages in PythonEmailMessage format
        while True:
            items = self.read_ews_account.inbox.filter(query).order_by('-datetime_received')[0:number]
            if not items:
                break  # No more emails to process
            for item in items:
                print(f"Subject: {item.subject}, Received: {item.datetime_received}")
                # Process each message as needed
                python_messages.append(self._transform_exchange_message_to_email(item))
            # offset += number  # Move to the next set of items

        # return the fetched emails
        return python_messages
    
    """
    Fetches emails using the IMAP protocol
    """
    def _fetch_emails_imap(self, criteria: dict, number: int = 10):
        self.logger.info("[IMAP] Fetching %s emails with filters: %s" % (number, criteria))

        # Building the search criteria
        imap_criteria = {}
        if criteria["from_date"]:
            imap_criteria['date_gte'] = datetime.date(criteria["from_date"])
        if criteria["to_domains"]:
            imap_criteria['to'] = criteria["to_domains"]
        if criteria["from_domains"]:
            imap_criteria['from_'] = criteria["from_domains"]
        if criteria["subject"]:
            imap_criteria['subject'] = criteria["subject"]
        # By default, imap_tools fetches all emails, including seen ones, so no need to use the imap_criteria['seen'] filter
        
        # Combine all criteria with AND
        search_criteria = AND(**imap_criteria)
        
        # Fetching emails based on the constructed criteria
        python_messages = []  # To store the messages in PythonEmailMessage format
        count = 0
        msgs = self.read_imap_mailbox.fetch(search_criteria, charset='utf-8', mark_seen=True, bulk=True,limit=number)
        # all_msgs=list(msgs)
        
        for msg in msgs:
            # Unluckily, imap_tools does not support searching after a specific time and only allows using dates
            # Therefore, we need to manually filter the emails based on the datetime_received
            # https://github.com/ikvk/imap_tools/issues/12 
            # https://datatracker.ietf.org/doc/html/rfc3501#:~:text=the%20specified%20date.-,SINCE%20%3Cdate%3E,-Messages%20whose%20internal
            if criteria["from_date"]:
                if msg.date.astimezone() < criteria["from_date"]:
                    continue
            
            if count >= number:
                break
            
            email_msg = self.mailconverter.convert_from_imapmessage(msg)

            python_messages.append(email_msg)
            count += 1
        
        # return the fetched emails
        return python_messages

    ############################
    # SENDING EMAILS FUNCTIONS #
    ############################
    """
    Sends an email to the user's email account
    It abstracts the sending process to allow Maitm to send emails using different protocols
    """
    def send_email(self, email: PythonEmailMessage):
        if (self.send_protocol == MailProtocols.EWS or self.send_protocol == MailProtocols.OAUTH2 or self.send_protocol == MailProtocols.OAUTH2LEGACY):
            self.send_exchange(email)
        elif(self.send_protocol == MailProtocols.SMTP):
            self.send_smtp(email)
        else:
            self.logger.error("Unsupported protocol for sending emails")

    """
    Sends an email using the SMTP protocol
    """
    def send_smtp(self, email: PythonEmailMessage):
        self.logger.info("[SMTP] Sending email with subject: %s" % email['Subject'])
        self.logger.debug("[SMTP] Email headers: ")
        for key in email.keys():
            self.logger.debug(f" [H] {key}: {email[key]}")
        self.send_smtp_connection.send_message(email)

    """
    Sends an email using the exchangelib library
    """
    def send_exchange(self, email: PythonEmailMessage):
        self.logger.info("[EXCHANGELIB] Sending email with subject: %s" % email['Subject'])
        sending_account = self.send_ews_account if self.send_ews_account else self.send_oauth2_account
        exchange_message = self.mailconverter.convert_to_exchange_message(email, sending_account)
        
        if exchange_message:
            return exchange_message.send()
        else:
            return False