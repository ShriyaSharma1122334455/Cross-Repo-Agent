const test = require("node:test");
const assert = require("node:assert/strict");
const { getHistoryForCard } = require("../src/history.js");

test("getHistoryForCard returns an array", () => {
  assert.ok(Array.isArray(getHistoryForCard("tok_visa")));
});
