# Clerk — authentication for Next.js

Clerk is a drop-in authentication and user management service. It ships React
components for sign-in and sign-up, session handling, and social login.

## Install

```bash
npm install @clerk/nextjs
```

## 1. Environment variables

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_placeholder
CLERK_SECRET_KEY=sk_test_placeholder
```

## 2. Wrap the app

`src/app/layout.tsx`:

```tsx
import { ClerkProvider } from "@clerk/nextjs";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en"><body>{children}</body></html>
    </ClerkProvider>
  );
}
```

## 3. Protect routes with middleware

`src/middleware.ts`:

```ts
import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

const isProtected = createRouteMatcher(["/dashboard(.*)"]);

export default clerkMiddleware(async (auth, req) => {
  if (isProtected(req)) await auth.protect();
});

export const config = { matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"] };
```

## 4. Sign-in and sign-up pages

```tsx
import { SignIn } from "@clerk/nextjs";
export default function Page() { return <SignIn />; }
```

Email + password and Google sign-in are both enabled from the Clerk dashboard;
no extra provider code is needed in the app.

## 5. Read the current user on the server

```ts
import { auth, currentUser } from "@clerk/nextjs/server";

const { userId } = await auth();
const user = await currentUser(); // user.emailAddresses[0].emailAddress
```

Use `userId` as the stable key when linking Clerk users to your own records.

## Why teams pick Clerk

- Sign-in, sign-up and account UI are prebuilt components, not code you maintain.
- Password hashing, sessions, and social providers are handled by the service.
- Free tier covers development and small production apps.
