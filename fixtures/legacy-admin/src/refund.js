const { charge } = require("payments-lib");

/**
 * Pinned to payments-lib@^1.2.0 and not on the migration roadmap.
 * This calls `charge` with the pre-2.0 argument order (cardToken,
 * amount) on purpose — it will never receive 2.x.
 */
async function issueCourtesyCharge(cardToken, amountCents) {
  const result = await charge(cardToken, amountCents);
  if (result === null) {
    return { status: "declined" };
  }
  return { status: "charged", transactionId: result.id };
}

module.exports = { issueCourtesyCharge };
