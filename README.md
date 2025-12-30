# RelayMail

**The Developer-First Transactional Email API**

RelayMail is a high-performance, minimalist email delivery service designed for developers who demand speed, simplicity, and aesthetics. We stripped away the complexity of traditional mailing services to provide a streamlined experience that lets you focus on shipping code.

---

## 🚀 Why RelayMail?

-   **Zero Configuration**: Stop wrestling with SMTP servers. Use our modern SDK.
-   **Instant Delivery**: Optimized specifically for transactional payloads (OTPs, Alerts, Welcome Emails).
-   **Beautiful Dashboard**: A "Command Center" inspired by high-end OS design to manage your logs and keys.
-   **Developer Centric**: Typescript-ready SDK, simple API authentication, and instant feedback.

---

## ⚡ How It Works

Get up and running in less than 30 seconds:

### 1. Sign Up
Create your account on the [RelayMail Dashboard](https://relaymail.pythonanywhere.com). No credit card required for the developer tier.

### 2. Generate an API Key
Navigate to your **API Keys** section and generate a secure access token. 
*Note: Your key is only shown once for security—keep it safe.*

### 3. Install the SDK
Add our lightweight package to your Node.js project:

```bash
npm install relaymail
```

### 4. Send Your First Email
Import the library and send an email with just 3 lines of code:

```javascript
import { RelayMail } from 'relaymail';

const mailer = new RelayMail('rk_live_...');

await mailer.send({
  to: 'user@example.com',
  subject: 'Welcome aboard! 🚀',
  content: 'Your account has been successfully created.'
});
```

---

## 🛡️ License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built for developers, by developers.</strong><br>
  <a href="https://relaymail.com">Start Sending Today</a>
</p>
