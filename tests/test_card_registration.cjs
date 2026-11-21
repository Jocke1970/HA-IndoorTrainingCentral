// UI smoke test: the new card and installed legacy card alias both load.
const fs = require("node:fs");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const code = fs.readFileSync("custom_components/homefitnesscode/www/homefitnesscode-card.js", "utf8");
const registry = new Map();
const scope = {
  HTMLElement: class {},
  window: {customCards: []},
  customElements: {
    get(name){return registry.get(name);},
    define(name, cls){registry.set(name, cls);}
  }
};
vm.runInNewContext(code, scope);
assert.equal(registry.has("homefitnesscode-card"), true);
assert.equal(registry.has("indoor-training-central-card"), true);
assert.equal(scope.window.customCards.length, 1);
assert.equal(scope.window.customCards[0].type, "indoor-training-central-card");
vm.runInNewContext(code, scope);
assert.equal(scope.window.customCards.length, 1);
console.log("IndoorTrainingCentral UI registration smoke test passed");
