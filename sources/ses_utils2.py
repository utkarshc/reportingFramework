import boto3

import matplotlib.pyplot as plt
from email import encoders
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from uuid import uuid4
import datetime
import base64

class SESClient:
    def __init__(self):
        self.a = "";


    def send_email(self, from_email, to_emails, subject, body_html, attachments=[], cc=[], bcc=[]):
        attachment_ready_html = []
        img_id = 0
        mime_images = []
        # iterate over raw HTML
        for l in body_html:
            # For each image in the body_html, convert each to a base64 encoded inline image
            if l.startswith("<img"):
                image_data = l[len("<img src='data:image/png;base64,"):-2]
                mime_img = MIMEImage(base64.standard_b64decode(image_data))
                mime_img.add_header('Content-ID', '<img-%d>' % img_id)
                attachment_ready_html.append("<center><img src='cid:img-%d'></center>" % img_id)
                img_id += 1
                mime_images.append(mime_img)
            else:
                attachment_ready_html.append(l)
        print("Added {} images".format(img_id))

        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = ", ".join(to_emails)
        body = MIMEText('\n'.join(attachment_ready_html), 'html')

        for i in mime_images:
            msg.attach(i)

        msg.attach(body)

        for raw_attachment in attachments:
            attachment = MIMEApplication(open(raw_attachment, 'rb').read())
            attachment.add_header('Content-Disposition', 'attachment', filename=raw_attachment)
            msg.attach(attachment)

        ses = boto3.client('ses', region_name='us-east-1')
        ses.send_raw_email(
            Source=msg['FROM'],
            Destinations=to_emails,
            RawMessage={'Data': msg.as_string()},
            SourceArn='arn:aws:ses:us-east-1:191195949309:identity/mindtickle.com',
            ReturnPathArn='arn:aws:ses:us-east-1:191195949309:identity/mindtickle.com')
        print "Sending Email."


    def makeCompatibleImage(self, imageName):
        with open(imageName) as png:
            val = "<img src='data:image/png;base64,%s'>" % base64.standard_b64encode(png.read())
        displayHTML(val)
        return val