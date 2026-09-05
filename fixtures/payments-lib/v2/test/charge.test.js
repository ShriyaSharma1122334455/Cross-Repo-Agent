const test = require("node:test");
const assert = require("node:assert/strict");
const { charge, PaymentDeclinedError } = require("../index.js");

test("charge resolves a successful transaction", async () => {
  const result = await charge(1000, "tok_visa");
  assert.equal(result.status, "succeeded");
  assert.ok(result.id);
});

test("charge rejects a non-positive amount", async () => {
  await assert.rejects(() => charge(0, "tok_visa"), TypeError);
});
