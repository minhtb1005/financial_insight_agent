import { withAuth } from "next-auth/middleware"

// Next 16 renamed middleware.ts -> proxy.ts (old filename is deprecated).
// Public paths (login/signup/next-auth/api-health) bypass auth so the
// container healthcheck and login flow work unauthenticated. In-app pages
// additionally enforce getServerSession themselves (defense in depth).
export default withAuth({
  pages: { signIn: "/login" },
})

export const config = {
  matcher: ["/((?!api/health|api/auth|login|signup|_next/static|_next/image|favicon.ico).*)"],
}
