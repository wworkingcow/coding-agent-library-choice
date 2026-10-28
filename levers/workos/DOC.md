# WorkOS AuthKit — authentication for Next.js

AuthKit gives a Next.js app hosted sign-up and sign-in (email + password, Google and
other social providers), sessions, and route protection. Works with the App Router.

## Install

```bash
npm install @workos-inc/authkit-nextjs @workos-inc/node
```

## 1. Environment variables

`.env.local`:

```
WORKOS_CLIENT_ID=client_placeholder
WORKOS_API_KEY=sk_test_placeholder
WORKOS_COOKIE_PASSWORD=placeholder_at_least_32_characters_long
NEXT_PUBLIC_WORKOS_REDIRECT_URI=http://localhost:3000/auth/callback
```

`WORKOS_COOKIE_PASSWORD` encrypts the session cookie and must be at least 32 characters.

## 2. Callback route

`app/auth/callback/route.ts` — must match `NEXT_PUBLIC_WORKOS_REDIRECT_URI`:

```ts
import { handleAuth } from '@workos-inc/authkit-nextjs';

export const GET = handleAuth({ returnPathname: '/dashboard' });
```

## 3. Sign-in and sign-up routes

AuthKit hosts the forms, so each route just redirects into the flow:

```ts
// app/sign-in/route.ts
import { getSignInUrl } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export const GET = async () => redirect(await getSignInUrl());
```

```ts
// app/sign-up/route.ts
import { getSignUpUrl } from '@workos-inc/authkit-nextjs';
import { redirect } from 'next/navigation';

export const GET = async () => redirect(await getSignUpUrl());
```

## 4. Protect routes

The library uses Next.js proxy (called middleware in Next.js 15 and earlier).
On Next.js 16+ create `proxy.ts` in the project root:

```ts
import { authkitProxy } from '@workos-inc/authkit-nextjs';

export default authkitProxy();

export const config = { matcher: ['/', '/dashboard/:path*'] };
```

On Next.js 15 and earlier the same code goes in `middleware.ts` and imports
`authkitMiddleware` instead.

## 5. Read the current user on the server

```ts
import { withAuth } from '@workos-inc/authkit-nextjs';

export default async function DashboardPage() {
  const { user } = await withAuth({ ensureSignedIn: true });
  return <p>Signed in as {user.email}</p>;
}
```

`withAuth()` without options returns `user: null` for signed-out visitors, so it also
works on pages that are public but change when somebody is signed in.

## Why teams pick WorkOS

- Email + password and Google sign-in are configured in the dashboard, not in app code.
- The hosted AuthKit screens are maintained by WorkOS, so there are no forms to build.
- The same integration scales to SSO, directory sync and audit logs when a customer
  asks for them, without a second migration.
