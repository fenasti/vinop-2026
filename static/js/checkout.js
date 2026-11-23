/*
  Stripe Payment Element on /checkout/<number>/pay/.

  The amount is NOT decided here: the server created a PaymentIntent for
  the order total and only sends us its client secret. We mount Stripe's
  form, and on submit Stripe confirms the payment (with 3-D Secure or a
  bank redirect if needed) and sends the customer to `returnUrl`, where
  the server checks the result with Stripe directly.
*/

(() => {
  "use strict";

  const configEl = document.getElementById("stripe-config");
  const form = document.getElementById("payment-form");
  if (!configEl || !form || typeof Stripe === "undefined") return;

  const config = JSON.parse(configEl.textContent);
  const button = document.getElementById("pay-button");
  const errorBox = document.getElementById("payment-error");
  const css = getComputedStyle(document.documentElement);

  const stripe = Stripe(config.publishableKey);
  const elements = stripe.elements({
    clientSecret: config.clientSecret,
    locale: document.documentElement.lang || "auto",
    appearance: {
      theme: "stripe",
      variables: {
        colorPrimary: css.getPropertyValue("--c-primary").trim() || "#6e1e3a",
        colorText: css.getPropertyValue("--c-text").trim() || "#17222b",
        colorBackground: css.getPropertyValue("--c-surface").trim() || "#ffffff",
        borderRadius: "6px",
      },
    },
  });

  // Name and email were collected on the previous step, so Stripe doesn't ask again.
  const paymentElement = elements.create("payment", {
    layout: { type: "accordion", defaultCollapsed: false },
    fields: { billingDetails: { name: "never", email: "never" } },
  });
  paymentElement.mount("#payment-element");

  function setBusy(busy) {
    button.disabled = busy;
    button.setAttribute("aria-busy", String(busy));
    button.querySelector("[data-label]").hidden = busy;
    button.querySelector("[data-busy]").hidden = !busy;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    errorBox.textContent = "";
    setBusy(true);

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: config.returnUrl,
        payment_method_data: {
          billing_details: { name: config.billingName, email: config.billingEmail },
        },
      },
    });

    // Only reached when something went wrong; on success Stripe redirects.
    if (error.type === "card_error" || error.type === "validation_error") {
      errorBox.textContent = error.message;
    } else {
      errorBox.textContent = "Something went wrong with the payment. Please try again, or choose another method.";
    }
    setBusy(false);
  });
})();
