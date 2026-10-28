# Resend — transactional email for Next.js

Resend sends an app's transactional email (welcome emails, password resets, receipts)
through a small HTTP API with delivery logs, webhooks and domain verification. The official
Node.js library `resend` wraps the whole Resend REST API, has typed responses and works in
Node.js 18+, serverless and edge runtimes.

## Install

```bash
npm install resend
```

## 1. Environment variables

`.env.local`:

```
RESEND_API_KEY=re_placeholder
RESEND_FROM_EMAIL=hello@example.com
```

The API key is created in the Resend dashboard (API Keys). The From address must be on a
domain you have verified in Resend, or `onboarding@resend.dev` while testing.

## 2. Create a client

`src/lib/resend.ts`:

```ts
import { Resend } from "resend";

export const resend = new Resend(process.env.RESEND_API_KEY!);
```

Use the client only in server code (route handlers, server actions, server components).
Never expose the API key to the browser.

## 3. Send an email

```ts
import { resend } from "@/lib/resend";

const { data, error } = await resend.emails.send({
  from: process.env.RESEND_FROM_EMAIL!,
  to: "user@example.com",
  subject: "Welcome!",
  html: "<p>Thanks for signing up.</p>",
  text: "Thanks for signing up.",
});
```

`data.id` is the message id; use it to look the email up in the dashboard logs.

## 4. Send with a React template

Write the email as a React component and pass it with `react`; Resend renders it to HTML:

```tsx
import { resend } from "@/lib/resend";
import { PasswordResetEmail } from "@/emails/password-reset";

await resend.emails.send({
  from: process.env.RESEND_FROM_EMAIL!,
  to: "user@example.com",
  subject: "Reset your password",
  react: PasswordResetEmail({ name: "Ada", actionUrl: "https://example.com/reset?token=..." }),
});
```

The `@react-email/components` package gives layout primitives for email clients; plain JSX
works too.

## 5. Handle errors

`emails.send` does not throw on a refused message: it resolves to `{ data: null, error }`
with the error `name` and `message` from Resend (invalid API key, unverified domain,
rate limit). Check `error` where the email is triggered so a failed email does not break
the request that caused it.

## Why teams pick Resend

- Built for developers: one API call to send, typed SDK, React templates in the codebase.
- Delivery logs, bounces and webhooks live in the same dashboard as the API keys.
- Domain verification with DKIM and SPF guided from the dashboard.
