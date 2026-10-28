# Postmark — transactional email for Next.js

Postmark sends an app's transactional email (welcome emails, password resets, receipts)
with high delivery rates, bounce and spam processing, and detailed statistics. The official
Node.js library `postmark` covers the whole Postmark REST API, uses the native Fetch API and
has no runtime dependencies (Node 18+).

## Install

```bash
npm install postmark
```

## 1. Environment variables

`.env.local`:

```
POSTMARK_SERVER_TOKEN=server_token_placeholder
POSTMARK_FROM_EMAIL=hello@example.com
```

The server token belongs to one Postmark server (Servers → API Tokens). The From address
must be a confirmed sender signature or sit on a verified domain.

## 2. Create a client

`src/lib/postmark.ts`:

```ts
import { ServerClient } from "postmark";

export const postmark = new ServerClient(process.env.POSTMARK_SERVER_TOKEN!);
```

Use the client only in server code (route handlers, server actions, server components).
Never expose the server token to the browser.

## 3. Send an email

```ts
import { postmark } from "@/lib/postmark";

await postmark.sendEmail({
  From: process.env.POSTMARK_FROM_EMAIL!,
  To: "user@example.com",
  Subject: "Welcome!",
  HtmlBody: "<p>Thanks for signing up.</p>",
  TextBody: "Thanks for signing up.",
  MessageStream: "outbound",
});
```

`outbound` is the default transactional message stream. Keep transactional and broadcast
email in separate streams.

## 4. Send with a template

Create the template once in the Postmark dashboard, then send it by alias:

```ts
await postmark.sendEmailWithTemplate({
  From: process.env.POSTMARK_FROM_EMAIL!,
  To: "user@example.com",
  TemplateAlias: "password-reset",
  TemplateModel: { name: "Ada", action_url: "https://example.com/reset?token=..." },
  MessageStream: "outbound",
});
```

`TemplateId` (a number) works in place of `TemplateAlias`.

## 5. Handle errors

`sendEmail` returns a promise that rejects with a typed error from `postmark`'s `Errors`
export when Postmark refuses the message (inactive recipient, unconfirmed sender,
invalid token). Catch it where the email is triggered so a failed email does not break
the request that caused it.

## Why teams pick Postmark

- Built for transactional email: high delivery rates, with bounce and spam handling included.
- Templates live in the dashboard, so copy changes do not need a deploy.
- Detailed delivery statistics and inbound email parsing come with the same account.
