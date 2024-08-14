from imap_tools.message import MailMessage as ImapMessage
from email import message_from_string
from email.message import EmailMessage as PythonEmailMessage
from email.mime.image import MIMEImage
from exchangelib import Message as ExchangeMessage, FileAttachment, Account as ExchangeAccount, HTMLBody, Mailbox as ExchangeMailbox
import mimetypes
import base64
import logging.config
import os
import yaml
import email
from email import policy
from email.parser import BytesParser

"""
MailConverter class is used to convert mail from one format to another.
It accepts exchangelib and imap_tools mail objects and converts it to python native email object.
It cannot do the reverse conversion to imap_tools message format, as it has immutable fields and is not needed to send out emails.
"""
class MailConverter:
    def __init__(self, exchangelib_mail: ExchangeMessage=None, exchange_account: ExchangeAccount=None, imap_tools_mail=None, clone_cc=False, clone_bcc=False, logfile="logs/mailconverter.log"):
        self.init_logging(log_filename=logfile)
        self.exchange_account = exchange_account
        self.exchange_mail = exchangelib_mail
        self.imap_mail = imap_tools_mail
        self.python_mail = PythonEmailMessage() 
        self.clone_cc = clone_cc
        self.clone_bcc = clone_bcc

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
    This function transforms an imap_tools message to a Python EmailMessage
    """
    def convert_from_imapmessage(self, msg: ImapMessage):
        raw_email = msg.obj.as_bytes()
        
        # Parse the raw email data
        self.python_mail = BytesParser(policy=policy.default).parsebytes(raw_email)
        # Add the UID attribute as well from the IMAP library
        self.python_mail['uid'] = msg.uid
        # Remove the Copied and BCC recipients
        del self.python_mail['cc']
        del self.python_mail['bcc']
        # Remove the 'received' header which may disclose our mail server address
        del self.python_mail['Received']
        del self.python_mail['Authentication-Results']
        del self.python_mail['Delivered-To']
        # Remove the 'spam' headers
        for header in list(self.python_mail.keys()):
            if 'spam' in header.lower():
                del self.python_mail[header]
        
        return self.python_mail
    
    """
    This function transforms an exchangelib message to a Python EmailMessage
    """
    def convert_from_exchangemail(self, msg: ExchangeMessage):
        raw_mime_content = msg.mime_content

        # Parse the raw MIME content
        self.python_mail = BytesParser(policy=policy.default).parsebytes(raw_mime_content)
        self.python_mail['uid'] = msg.id+"-"+msg.changekey
        # Remove the Copied and BCC recipients
        del self.python_mail['cc']
        del self.python_mail['bcc']
        # Remove the 'received' header which may disclose our mail server address
        del self.python_mail['Received']
        del self.python_mail['Authentication-Results']
        del self.python_mail['Delivered-To']
        # Remove the 'spam' headers
        for header in list(self.python_mail.keys()):
            if 'spam' in header.lower():
                del self.python_mail[header]

        return self.python_mail
    
    """
    This function transforms a Python EmailMessage to an exchangelib message format
    """
    def convert_to_exchange_message(self, msg: PythonEmailMessage, exchage_account: ExchangeAccount = None):
        # Create a new ExchangeMessage object
        if exchage_account:
            self.exchange_account = exchage_account
        if not self.exchange_account:
            self.logger.error("Exchange account is not provided")
            return None
        self.exchange_mail = ExchangeMessage(account=self.exchange_account)

        self.exchange_mail.body = HTMLBody(msg.get_body(preferencelist=('html',)).get_content())
        self.exchange_mail.subject = msg['Subject']
        self.exchange_mail.to_recipients = [ExchangeMailbox(email_address=addr) for addr in msg.get_all('To', [])]
        # TODO: Not sure if I can spoof the sender with exchangelib. Proably need to use the account's email address
        self.exchange_mail.sender = ExchangeMailbox(email_address=msg['From'])
        
        # Handling CC and BCC if needed
        # TODO: Change the CC and Bcc handing 
        if msg.get_all('Cc', []):
            self.exchange_mail.cc_recipients = [ExchangeMailbox(email_address=addr) for addr in msg.get_all('Cc', [])]
        if msg.get_all('Bcc', []):
            self.exchange_mail.bcc_recipients = [ExchangeMailbox(email_address=addr) for addr in msg.get_all('Bcc', [])]

        # Add attachments
        for part in msg.iter_parts():
            if part.get_content_disposition() == 'attachment':
                content_type = part.get_content_type()
                maintype, subtype = content_type.split('/')
                attachment = FileAttachment(
                    name=part.get_filename(),
                    content=part.get_payload(decode=True),
                    content_type=content_type
                )
                self.exchange_mail.attach(attachment)

        return self.exchange_mail