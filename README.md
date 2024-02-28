Summary
=======

<p align="center">
  <img src="img/maitm.png" width=250px height=250px>
</p>

This script sits in the middle between a legitimate sender of an email and the legitimate recipient of that email. This means that we (the attackers) are receiving sensitive information not originally destined to us. I like to call these emails "Stranded emails".

The way we sit in the middle of these two parts are by taking advantage of the typos the sender of the email commits. The attacker needs to register multiple domains with typos of the target company, or what is usually called, [typosquatted](https://www.kaspersky.com/resource-center/definitions/what-is-typosquatting) domains. 

Once the typosquatted domains are on the attacker's hands, they should [configure an MX](https://www.namecheap.com/support/knowledgebase/article.aspx/322/2237/how-can-i-set-up-mx-records-required-for-mail-service/) entry on their DNS entries to redirect the emails to their mail server (e.g. mail.attackerdomain.com). Then, the mail server have to be configured with a [catch-all](https://tecadmin.net/setup-catch-all-email-account-in-postfix/) rule to receive all emails in a single inbox (e.g. attacker@attackerdomain.com).

This script connects to the attacker mail server (mail.attackerdomain.com) and lists the emails being received there following a set of rules (filter rules). All the emails that match the filter will be forwarded to their legitimate recipients, but with a pinch of evilness. This means that we can modify the contents of the email, including attachments, links, tracking pixels, and other content. This opens an avenue to send phishing links or C2 beacons to users that are actually expecting an email with that content, thus, increasing our oportunities to get interactions with the targets.

Architecture
============
A picture is worth a thousand words.

Green email means "untainted" email. Red email means "tainted" email with attacker's controlled links, attachements, and content:

<img src="img/arch.png">

# Usage

## Configuration

Open the file "config/config.yml", configure the name of the files containing the sub-configuration files:
* auth: Contains the authentication information to login the SMTP and IMAP servers
* typos: Contains the rules to fix the typos in specific email addresses or domains
* filter: Contains the filtering settings of what emails to forward and poison
* injections: Contains the behaviour of the program regarding injecting tracking URLs, UNC paths and attachments
* misc: Contains various settings, including the source and destination addresses, and the interval to poll the mail boxes.
* notifications: Contains settings for Discord and Teams notification.
* logging: Contains the configuration of the logger.

For detailed information about how to configure each of these sub-configuration files, refer to the section ["Configuration files"](#configuration-files).

## Execution
Once the configuration has been done, you can invoke the script using docker or by installing the dependencies with pipenv.

## Flags
Use the flag "-f" to forward the emails for real (without this flag, the script would only  monitor the incoming emails and send them to the Discord/Teams chat).

The flag "-n" is important if you only want to monitor the "new" emails. If not specified, all the historic emails would be retrieved from the inbox on execution on every loop, so you would end up sending the same emails in each iteration of the polling loop. Use "-n" in production. Do not user if you want to test the script.

The flag "-c" is to provide alternative configuration files.

### Docker Execution
Build and execute the container by running this:
```bash
docker build -t maitm .       # Build
docker run --rm -ti maitm -h  # To get help
docker run --rm -ti maitm -c config/config.yml -f -n # To forward the emails and only forward newest emails
```

Change the configuration (-c) parameter and flags (-f, -n) per your needs.

### Pipenv Execution

Install pipenv on your environment, the dependencies and run:

```bash
apt install pipenv
pipenv install --python=3.10
pipenv shell
./mail-in-the-middle.py -n -f -c config/config.yml
```

Configuration files
===================

To see examples of the files, go to the folder config.

config.yml
----------
Root configuration file. It has one entry per sub-configuration file. The default content is:

```yaml
auth: auth.yml
filter: filter.yml
injections: injections.yml
misc: misc.yml
notifications: notifications.yml
typos: typos.yml
```

If you want to have multiple configuration files you can create conf-prod.yml, conf-dev.yml, conf-test.yml, etc. and modify single values in this structure, such as the auth or filter.

typos.yml
---------
These are the rules that Mail-in-the-middle follow to correct the destination email address and forward the tained email. We can define specific email addresses or whole domains. 
For example, if we want to fix a typo in the email felipe@mydomani.com and forward to felipe@mydomain.com and we want to forward emails sent to mircosoft.com, and micrrosoftr.com and send them to users of microsoft.com, we write the following:
```yaml
address:
  felipe@mydomani.com: felipe@mydomain.com
domain:
  mircosoft.com: microsoft.com
  micrrosoftr.com: microsoft.com
```

filter.yml
----------
The file allows you to define what emails are forwarded and tainted with your links and content. The following parameters can be defined:
* **from_domains**: A list of domains of the emails specified in the "From" field of the email.
* **to_domains**: A list of domains of the emails specified in the "To" field of the email.
* **ignore_to_domains**: A list of domains of the emails specified in the "To" field of the email to ignore.
* **subject_str**: A list of subjects of emails to forward. Like "OTP", "Registration", etc.
* **ignore_subjects**: A list of Subjects to ignore. If any of the previous filter matches (from_domains, to_domains, subject_srt), the email will not be forwarded if it contains the strings defined here.
* **date_limit**: A UTC date with the format YYYY-MM-DD HH:mm:ss+00.Forward emails only if are more recent than this date.

auth.yml
--------
Contains two sections. One for "smtp" and the other for "imap". The default content is self-explanatory:
```yaml
smtp:
  username: hacker@attacker.com
  password: 'Hunter2'
  server:  smtp.attacker.com
  port: 587
  tls: True
imap:
  username: hacker@attacker.com
  password: 'Hunter2'
  server: imap.attacker.com
  port: 993
  ssl: True
```

The two sections are separated to ease sending out emails from a different infrastructure than the email receiving infrastructure.

injections.yml
--------------
Define what to do with the email content.
It has four root keys:
* **tracking_url**: The URL of your tracking pixel. It gets injected at the beggining of the email within an ```<img>``` tag. 
* **unc_path**: The UNC path to exfiltrate NetNTLM tokens of your targets. It gets injected at the beggining of the email within an ```<img>``` tag.
* **attachments**: It defines what to do with the attachments of the emails. It has to contain the following attributes:
    * **replace_original**: If true, replace the original attachement with ours.
    * **inject_new**: If the email does not have an attachment, inject ours.
    * **path**: Path to our attachement.
    * **attachment_message**: HTML code to introduce at the beggining of the email to instruct your targets how to unzip and execute your payload ;-)
* **links**: It defines what to do with the original links of the email. It can contain the following attributes:
    * **all**: A URL with which ALL the links of the email will be replaced. 
    * **<domain.com>**: The first level domain of the links in the email that will be replaced with your URL. You can define more than 1. E.g. if you define office.com: https://attacker.com/notaphish.html, only the links pointing to \*.office.com/\* will be replaced with the attacker's defined link.

notifications.yml
-----------------
Two keys. One for "teams", other for "discord". Both optional.


License
=======
Maitm is licensed under a [GNU General Public v3 License](https://www.gnu.org/licenses/gpl-3.0.en.html). Permissions beyond the scope of this license may be available at http://sensepost.com/contact/.

Feedback
========
PRs are welcome. Please, let me know of any other ideas or suggestions via twitter [@felmoltor](https://twitter.com/felmoltor).

Original Idea
=============
Szymon Ziolkowski ([@TH3_GOAT_FARM3R](https://twitter.com/TH3_GOAT_FARM3R)). Felipe Molina ([@felmoltor](https://twitter.com/felmoltor)) was just the dev and increased the original functionality :-)