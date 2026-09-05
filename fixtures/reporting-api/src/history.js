const { getTransactionHistory } = require("payments-lib");

/**
 * Returns a card's transaction history for the dashboard endpoint.
 * This service only ever reads history — it never initiates a charge,
 * so changes to `charge()` don't reach it.
 */
function getHistoryForCard(cardToken) {
  return getTransactionHistory(cardToken).map((txn) => ({
    id: txn.id,
    amount: txn.amount,
    status: txn.status,
  }));
}

module.exports = { getHistoryForCard };
