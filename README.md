# VinOp 2026 — Chilean wines for Europe

An online wine shop that imports from small Chilean producers and sells to
customers across the EU. Mobile first, desktop friendly, Stripe payments,
customer accounts, and a full **team area at `/team/`** with roles, so all
day-to-day work (wines, stock, orders, shipping, reviews, newsletter, legal
pages, site design) happens **without the Django admin**. The Django admin
isn't installed at all.

Rebuilt from scratch from [fenasti/vinop_p5](https://github.com/fenasti/vinop_p5),
with the team-area ideas from the jewelry shop (role hub, Studio, packing-list
export). Every bug found in the original is fixed — see
[Bugs fixed](#bugs-fixed-from-the-first-vinop).

| | |
|---|---|
| Python | 3.12 – 3.14 (`.python-version` says 3.14, the newest Django 5.2 supports) |
| Django | 5.2 LTS (`Django>=5.2,<5.3`, security support until April 2028) |
| Accounts | django-allauth 65 (email login, email verification, password reset) |
| Payments | Stripe Payment Element + webhooks (stripe-python 16, `StripeClient`) |
| Static files | WhiteNoise · optional S3 for uploaded photos |
| Database | SQLite locally, PostgreSQL in production (`DATABASE_URL`) |
| Front end | Hand-written CSS + ~150 lines of vanilla JS. No Bootstrap, no jQuery |

---

## 1. Run it on your Mac

```bash
cd vinop-2026
python3.14 -m venv .venv            # 3.12 or 3.13 also work
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                # then open .env and fill in SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"   # paste this as SECRET_KEY

python manage.py migrate            # also creates the four team roles
python manage.py seed_demo          # regions, grapes, legal pages, 18 demo wines
python manage.py createsuperuser    # your owner account (use your email)
python manage.py runserver
```

Open http://127.0.0.1:8000. Log in at `/accounts/login/` **with your email**.

> **Side note: the first login asks you to confirm your email.** With
> `ACCOUNT_EMAIL_VERIFICATION=mandatory`, allauth sends a confirmation email.
> In development emails are printed in the terminal running `runserver`:
> copy the link from there. To skip it locally, set
> `ACCOUNT_EMAIL_VERIFICATION=optional` in `.env`.

After logging in as the superuser you land on **`/team/`**.

### Run the tests

```bash
python manage.py test        # 71 tests, Stripe is mocked, runs offline in ~5 s
```

### Put it on GitHub

`.gitignore` already keeps `.env`, the database and uploads out of the repo.

```bash
git init -b main
git add -A
git commit -m "VinOp 2026: Django 5.2 rebuild"
gh repo create vinop-2026 --private --source=. --push   # or create it on github.com and `git push`
```

---

## 2. Payments with Stripe (test mode)

1. Copy your **test** keys from https://dashboard.stripe.com/test/apikeys into
   `.env` (`STRIPE_PUBLIC_KEY=pk_test_…`, `STRIPE_SECRET_KEY=sk_test_…`).
2. In another terminal, forward webhooks to your laptop
   ([Stripe CLI](https://docs.stripe.com/stripe-cli)):
   ```bash
   stripe login
   stripe listen --forward-to localhost:8000/checkout/webhook/
   ```
   It prints `whsec_…`: put it in `.env` as `STRIPE_WEBHOOK_SECRET` and restart `runserver`.
3. Buy something. Test payment details:

   | What | Use |
   |---|---|
   | Card that works | `4242 4242 4242 4242`, any future date, any CVC |
   | Card with 3-D Secure | `4000 0027 6000 3184` |
   | Declined card | `4000 0000 0000 0002` |
   | SEPA Direct Debit | IBAN `DE89 3704 0044 0532 0130 00` (stays "waiting for the bank", then confirms) |

Which methods appear (cards, Apple/Google Pay, SEPA, iDEAL, Bancontact, Klarna…)
is switched on in the Stripe dashboard under *Settings → Payment methods*; the
code doesn't need to change.

### How a payment flows (and why)

```
/checkout/             delivery form ──► PENDING order (totals computed on the server)
/checkout/VO-…/pay/    Stripe Payment Element for exactly order.total
        │  customer pays (3-D Secure / bank redirect if needed)
        ▼
/checkout/VO-…/complete/   asks Stripe for the result ─┐
/checkout/webhook/         Stripe tells us directly   ─┴─► mark_paid()  (runs once)
                                                          invoice no., stock −, emails
```

`orders/services.py::mark_paid()` locks the order row and only acts while it is
still PENDING, so the return page and the webhook can both call it safely.

---

## 3. The team area and roles

Roles are Django groups, created automatically by `migrate`. What each one can
open is written in **one place**: `team/permissions.py`.

| Role | Can open |
|---|---|
| **Shop Manager** | Everything, including team roles and legal pages |
| **Cellar Keeper** | Wines, wineries, regions, grapes, stock · moderates reviews |
| **Fulfilment** | Orders, packing list (CSV), mark shipped / delivered, cancel |
| **Site Editor** | The Studio only (homepage text, colours, fonts, logo, footer) |
| Superuser | Everything, always |

Give someone a role:

* in the browser: `/team/members/` (Shop Managers) — they sign up first, then you add them by email;
* or in the terminal: `python manage.py grant_role ana@example.com "Fulfilment"`.

What's in the team area:

* **Overview** — cards for every area you can open, revenue and orders in the last 30 days, wines running low.
* **Wines** — create, edit, delete (with a confirmation that explains what happens), hide/show with one click, set stock right in the list, preview hidden wines in the shop.
* **Wineries, Regions, Grapes** — full CRUD; a region or winery still in use can't be deleted by accident.
* **Orders** — tabs (to ship, shipped, awaiting payment, cancelled, all), search, order page with *mark as shipped* (emails the customer the tracking number), *mark delivered*, *cancel* (restocks), internal notes, **packing list CSV** for the courier.
* **Reviews** — publish/hide, delete.
* **Newsletter** — confirmed subscribers, CSV export (only confirmed addresses, with each person's unsubscribe link).
* **Legal pages** — imprint, privacy, terms, withdrawal, shipping. Pages still holding placeholder text show a TODO badge.
* **Studio** — how the shop looks, live on save. It warns when a colour choice makes text hard to read. Prices and shipping are deliberately *not* here.

---

## 4. Where things live

```
vinop/        settings (everything configurable through .env), urls
core/         homepage, legal pages, shared email helper, {% icon %} and |money, seed_demo
studio/       SiteSettings: the look of the shop (colours, fonts, texts)
catalog/      Region → Winery → Wine ← Grape; list with filters, wine page
cart/         session cart (cart.py) and the money rules (pricing.py)
orders/       Order, OrderItem, checkout views, Stripe (payments.py), webhooks, services, emails
accounts/     Profile (saved address), order history, delete account, login redirect
wishlist/     one row per saved wine
reviews/      one review per customer per wine
newsletter/   double opt-in subscribers
team/         the back office: permissions.py, mixins.py, views/, grant_role command
templates/    all HTML, incl. emails/, team/, allauth/ (allauth uses the shop layout)
static/       css/vinop.css (mobile first), js/site.js, js/checkout.js
```

Some conventions worth knowing:

* **Money** is always `Decimal`, rounded in one place (`cart/pricing.py`). Stripe gets integer cents from `to_cents()`.
* **Every form** renders through `templates/forms/field.html` (label, "optional" marker, help text, accessible error), so `{{ form }}` looks the same everywhere.
* **Every message** a user can see (`messages.success/warning/error`) says what happened and what to do next.
* **Strings are translatable** (`{% translate %}`, `gettext`). To add German: `python manage.py makemessages -l de`, translate `locale/de/LC_MESSAGES/django.po`, `compilemessages`, and add `("de", "Deutsch")` to `LANGUAGES`.

---

## 5. Bugs fixed from the first VinOp

| # | Where | Problem in vinop_p5 | Now |
|---|---|---|---|
| 1 | `checkout/webhook_handler.py` | `stripe` was never imported, so every successful-payment webhook crashed | Webhook handlers tested; Stripe lives in `orders/payments.py` |
| 2 | `checkout/views.py` | Empty bag redirected to `reverse('products')`, a URL that doesn't exist (crash) | Redirects to the wine list with a message |
| 3 | `checkout/views.py` | An invalid checkout form crashed: `intent` was undefined on POST | Form errors re-render the page |
| 4 | Checkout template | Said "Your card will be charged **total**" but charged **grand total** (incl. delivery) | One total, computed on the server, shown on the pay button |
| 5 | Webhook | Found orders by comparing 11 address fields; any difference created a duplicate order and email | Orders found by PaymentIntent id; `mark_paid()` is idempotent |
| 6 | `stripe_elements.js` | "Save info" read `attr('checked')` (the initial state), not the checkbox's real value | Saving the address is a normal form field |
| 7 | `profiles/views.py` | `/profile/order_history/<number>` showed **any** order to anyone who knew the number, no login needed | Only the owner (or the same browser for guests, or the Fulfilment team) |
| 8 | `checkout_success` | Same: any order visible by URL, and it re-attached the order to whoever opened it | Same access check |
| 9 | `bag/contexts.py` | `get_object_or_404` inside the context processor: deleting a wine made **every page 404** for anyone with it in the bag | Missing wines quietly drop out of the cart |
| 10 | `OrderLineItem` | `on_delete=CASCADE`: deleting a wine **deleted it from past orders** | `SET_NULL` + name and price snapshot on each item |
| 11 | Stock | Advertised stock tracking, but `Wine` had no stock field | Stock field, cart capped at stock, decremented once on payment, restored on cancel |
| 12 | `bag/views.py` | `int(request.POST.get('quantity'))` crashed on bad input; `redirect_url` allowed redirects to any website | Validated quantities; `core/utils.redirect_back()` only allows our own site |
| 13 | `bag.html` | `data-item_id="{{ wine.wine_id }}"` — `wine` didn't exist there, so the +/− buttons on the bag page did nothing | One reusable stepper include |
| 14 | `delete_wine`, wishlist add/remove, bag remove | Changed data on a **GET** link (no confirmation, CSRF-able) | All changes are POST; deletes ask first |
| 15 | Wishlist | Only created for users who signed up after the app was added (README "Bug 3"); old users crashed | A row per saved wine, nothing to create |
| 16 | Profile signal | `instance.userprofile.save()` crashed for users without a profile | `get_or_create`, plus `Profile.for_user()` |
| 17 | `subscriptions/views.py` | GET rendered `index.html`, which doesn't exist (crash) | POST-only subscribe |
| 18 | Newsletter | No confirmation, no unsubscribe (not allowed in the EU) | Double opt-in and one-click unsubscribe page |
| 19 | Newsletter email | `fail_silently=False`: an SMTP hiccup crashed the sign-up | Email failures are logged, never shown as a crash |
| 20 | Confirmation email | Said "Boutique Ado" | Shop name from the Studio |
| 21 | Reviews | Unlimited reviews per user, no edit or delete, HTML stars built in the model | One per user per wine, editable, deletable, team moderation |
| 22 | Profile form | The form was rebuilt after every POST, so validation errors were thrown away | Errors stay on the form; success redirects with a message |
| 23 | Settings | `STATICFILES_STORAGE` / `DEFAULT_FILE_STORAGE` were **removed in Django 5.1** | `STORAGES` setting |
| 24 | Settings | Currency `usd` for a European shop; hardcoded hosts; `DEBUG = 'DEVELOPMENT' in os.environ` | EUR, everything from `.env`, production security settings |
| 25 | Templates | Two elements with `id="user-options"`, `<li>` outside a `<ul>`, a personal Font Awesome kit | Valid markup, inline SVG icon sprite |
| 26 | Catalogue | Empty search showed an error; filters only matched exact text from the URL | Search across wine, winery, grape and region; filters ignore bad values |
| 27 | `lineitem_total` | `max_digits=6`: a line over €9,999.99 failed to save | `max_digits=10` |

---

## 6. Before you launch (business & legal checklist)

This is not legal advice, but these are the things a wine shop selling into
Germany/the EU usually has to sort out:

* **Legal pages** — the five pages from `seed_demo` hold placeholder text marked TODO. Imprint (§ 5 DDG), privacy policy (GDPR), terms, right of withdrawal with the model form, shipping. They probably need to be in German for German customers.
* **Alcohol** — the age check and the 18+ checkbox at checkout are in place; agree age verification on delivery with your carrier.
* **VAT and excise duty** — the homepage says "Duty and VAT included". Make sure that's how you import (excise and VAT rules differ per EU country, and selling to other EU countries may need OSS VAT registration). Change the text in `templates/core/home.html` if not.
* **Unit prices** — price per litre is shown everywhere, as German price law requires.
* **Allergens** — "Contains sulphites" is shown on every wine.
* **The order button** says "Buy now, pay €…", as German law requires a clear "order with obligation to pay" button.
* **Fonts** — the default fonts load nothing from Google. If you pick a Google font in the Studio, mention it in the privacy policy (or self-host it).
* **Demo data** — the 18 wines and 10 wineries are invented. Edit or delete them in `/team/wines/`.

---

## 7. Deploying (Heroku, Render, Railway…)

1. Create a PostgreSQL database and set `DATABASE_URL`.
2. Set the environment variables from `.env.example` with production values:
   `DEBUG=False`, a new `SECRET_KEY`, your domain in `ALLOWED_HOSTS`,
   `CSRF_TRUSTED_ORIGINS=https://yourdomain`, `SITE_URL=https://yourdomain`,
   SMTP settings with `EMAIL_USE_CONSOLE=False`, live Stripe keys when ready.
3. Build command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`.
   The `Procfile` runs `migrate` on each release and starts gunicorn.
4. Uploaded wine photos: most hosts wipe the disk on every deploy, so set `USE_S3=True`
   with your bucket (`AWS_STORAGE_BUCKET_NAME`, keys) and install `django-storages[s3]`.
5. Once, in the host's shell: `python manage.py seed_demo --no-wines` and `python manage.py createsuperuser`.
6. In the Stripe dashboard (*Developers → Webhooks*), add `https://yourdomain/checkout/webhook/`
   with `payment_intent.succeeded`, `payment_intent.payment_failed` and `charge.refunded`,
   and put its signing secret in `STRIPE_WEBHOOK_SECRET`.
7. After HTTPS works, raise `SECURE_HSTS_SECONDS` (e.g. `31536000`).

`python manage.py check --deploy` should then only mention the optional HSTS preload settings.
