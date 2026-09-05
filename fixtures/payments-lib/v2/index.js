class PaymentDeclinedError extends Error {
  constructor(cardToken) {
    super(`Payment declined for card ${cardToken}`);
    this.name = "PaymentDeclinedError";
  }
}

/**
 * Charges a card for the given amount.
 *
 * Resolves the transaction result. Declines are no longer a `null`
 * return — they throw `PaymentDeclinedError` so failures can't be
 * mistaken for success by a caller that forgets to check the result.
 *
 * BREAKING: argument order is now (amount, cardToken), matching the
 * rest of the client's method signatures. BREAKING: declines throw
 * instead of resolving `null`.
 *
 * @param {number} amount
 * @param {string} cardToken
 * @returns {Promise<{id: string, status: string}>}
 */
async function charge(amount, cardToken) {
  if (!cardToken || amount <= 0) {
    throw new TypeError("charge requires a cardToken and a positive amount");
  }

  const result = await processTransaction(cardToken, amount);
  if (result.declined) {
    throw new PaymentDeclinedError(cardToken);
  }

  return { id: result.transactionId, status: "succeeded" };
}

async function processTransaction(cardToken, amount) {
  // Simulated payment gateway call.
  return { declined: false, transactionId: `txn_${Date.now()}` };
}

/**
 * Returns prior transactions for a card token, most recent first.
 * @param {string} cardToken
 * @returns {Array<{id: string, amount: number, status: string}>}
 */
function getTransactionHistory(cardToken) {
  return [];
}

module.exports = { charge, getTransactionHistory, PaymentDeclinedError };
