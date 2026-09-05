const test = require("node:test");
const assert = require("node:assert/strict");
const { charge } = require("../index.js");

test("charge resolves a successful transaction", async () => {
  const result = await charge("tok_visa", 1000);
  assert.equal(result.status, "succeeded");
  assert.ok(result.id);
});

test("charge rejects a non-positive amount", async () => {
  await assert.rejects(() => charge("tok_visa", 0), TypeError);
});
