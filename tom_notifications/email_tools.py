# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 10:22:46 2019

@author: rstreet
"""

from django.conf import settings
from django.core.mail import send_mail

def send_email_to_mailing_list(subject, message, distribution_list):
    """Function to send an email notification
    
    Input parameters:
        subject             string  Subject line for the email
        message             string  Main content of the email
        distribution_list   list    Email addresses to send the message to
    """

    send_mail(subject,
              message,
              settings.EMAIL_HOST_USER,
              distribution_list,
              fail_silently=False,
              )
