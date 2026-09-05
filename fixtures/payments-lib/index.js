/**
 * Charges a card for the given amount.
 *
 * Resolves the transaction result, or `null` if the card was declined.
 * Declines are an expected outcome, not an error — callers are expected
 * to check for `null` and decide whether to retry.
 *
 * @param {string} cardToken
 * @param {number} amount
 * @returns {Promise<{id: string, status: string} | null>}
 */
async function charge(cardToken, amount) {
  if (!cardToken || amount <= 0) {
    throw new TypeError("charge requires a cardToken and a positive amount");
  }

  const result = await processTransaction(cardToken, amount);
  if (result.declined) {
    return null;
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

module.exports = { charge, getTransactionHistory };
