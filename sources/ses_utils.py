import boto3
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SESClient:
    def __init__(self, to, subject):
        self.ses = boto3.client('ses');
        self.to = to
        self.subject = subject
        self.text = None
        self.attachment = None

    def addAttachment(self, filename):
        self.file_name=filename;
        f = open(filename,"r");
        self.attachment = f.read();

    def addText(self, text):
        self.text = text;

    def sendMail(self, from_addr=None):
        msg = MIMEMultipart()
        msg['Subject'] = self.subject
        msg['From'] = from_addr
        msg['To'] = self.to

        part = MIMEApplication(self.attachment)
        part.add_header('Content-Disposition', 'attachment', filename=self.file_name)
        part.add_header('Content-Type', 'application/vnd.ms-excel; charset=UTF-8')

        msg.attach(part)

        # the message body
        part = MIMEText(self.text)
        msg.attach(part)

        # return self.ses.send_email(
        #     Source=from_addr,
        #     Destination={'ToAddresses': [self.to]},
        #     Message={
        #         'Body': {'Html': {'Charset': 'UTF-8',
        #                           'Data': msg.as_string()}},
        #         'Subject': {
        #             'Charset': 'UTF-8',
        #             'Data': self.subject}
        #     },
        #     SourceArn='arn:aws:ses:us-east-1:191195949309:identity/mindtickle.com',
        #     ReturnPathArn='arn:aws:ses:us-east-1:191195949309:identity/mindtickle.com'
        # );
        self.ses.send_raw_email()
