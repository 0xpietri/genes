// The place for a later login. Nobody logs in today (spec §1: no users), and the public pages
// must stay static files that every visitor shares, so a login never changes the HTML a page
// is built with. When one comes (marcos's admin panel first, see docs/reports/CATALOG_SITE.md),
// it plugs in here and only here:
//   - accounts live at id.pietri.dev (spec §2.3); the browser signs in there (OpenID Connect
//     with PKCE) and keeps a short-lived token; genes.pietri.dev itself stores nothing;
//   - currentAccount() resolves that account or null; pages call it after they are drawn and
//     add personal parts client-side (the header slot, an "edit this species" link for admins);
//   - anything an admin changes becomes files in the repository (a PR), rebuilt ahead of time,
//     so visitors still only download static, cached files.

/** The signed-in account, or null. Always null until a login exists. */
export async function currentAccount() {
  return null;
}

/** Fills the header's account slot (empty and hidden while there is no login). */
export async function mountAccount(slot = document.querySelector('[data-account-slot]')) {
  if (!slot) return null;
  const account = await currentAccount();
  if (!account) return null;
  slot.textContent = account.name ?? '';
  return account;
}
