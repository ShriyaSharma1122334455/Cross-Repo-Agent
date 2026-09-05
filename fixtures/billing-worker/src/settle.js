const { charge } = require("payments-lib");

/**
 * Attempts to settle one outstanding invoice.
 * A declined charge is expected under normal operation (insufficient
 * funds, temporary hold) — `charge` resolving `null` is how the retry
 * queue knows to try again on the next billing cycle instead of
 * writing off the invoice.
 */
async function settleInvoice(invoice, retryQueue) {
  const result = await charge(invoice.cardToken, invoice.amountCents);

  if (result === null) {
    retryQueue.scheduleRetry(invoice.id);
    return { invoiceId: invoice.id, status: "retry_scheduled" };
  }

  return { invoiceId: invoice.id, status: "paid", transactionId: result.id };
}

module.exports = { settleInvoice };
