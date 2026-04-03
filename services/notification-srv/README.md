### notification-srv

notification-srv consumes events published durably over [Apache Kafka](https://kafka.apache.org/).
Notifications are published by booking-srv when a new status is made available for a booking request.
The service will publish messages over websocket or email depending on the `delivery_type` field in the Kafka messages.

#### Email

Email is managed through [SendGrid/Twilio](https://www.twilio.com/en-us/sendgrid/).
To configure, create a SendGrid account.
Obtain an API key, and populate a `.env` file in this directory as follows:

```txt
SENDGRID_API_KEY=<your API key>
SENDGRID_FROM_EMAIL=<your From: email>
```

Email sending using a `gmail.com` or similar public personal domain is likely to fail due to DMARC authentication.
Emails will normally send to the same email they are being sent from, though may often end up in spam.
