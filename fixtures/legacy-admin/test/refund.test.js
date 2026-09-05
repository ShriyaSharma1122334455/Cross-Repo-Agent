const test = require("node:test");
const assert = require("node:assert/strict");
const { issueCourtesyCharge } = require("../src/refund.js");

test("issueCourtesyCharge reports a charged status on success", async () => {
  const result = await issueCourtesyCharge("tok_visa", 1500);
  assert.equal(result.status, "charged");
});
