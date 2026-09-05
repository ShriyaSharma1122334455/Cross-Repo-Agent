const test = require("node:test");
const assert = require("node:assert/strict");
const { settleInvoice } = require("../src/settle.js");

test("settleInvoice marks a successful charge as paid", async () => {
  const result = await settleInvoice(
    { id: "inv_1", cardToken: "tok_visa", amountCents: 5000 },
    { scheduleRetry: () => {} },
  );
  assert.equal(result.status, "paid");
  assert.ok(result.transactionId);
});
