const test = require("node:test");
const assert = require("node:assert/strict");
const { completeCheckout } = require("../src/checkout.js");

test("completeCheckout returns a receipt with a transaction id", async () => {
  const receipt = await completeCheckout({
    orderId: "order_1",
    cardToken: "tok_visa",
    totalCents: 2500,
  });
  assert.equal(receipt.orderId, "order_1");
  assert.equal(receipt.total, 2500);
  assert.ok(receipt.transactionId);
});
