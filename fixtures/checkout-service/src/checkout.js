const { charge } = require("payments-lib");

/**
 * Captures payment for a cart and returns a receipt.
 * Assumes the charge succeeds; failure handling lives upstream in the
 * gateway webhook, not here.
 */
async function completeCheckout(cart) {
  const result = await charge(cart.cardToken, cart.totalCents);
  return {
    orderId: cart.orderId,
    transactionId: result.id,
    total: cart.totalCents,
  };
}

module.exports = { completeCheckout };
