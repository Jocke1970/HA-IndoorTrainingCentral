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
    define(name, cls){
      if(registry.has(name) || [...registry.values()].includes(cls)){
        throw new Error("NotSupportedError: tag or constructor already registered");
      }
      registry.set(name, cls);
    }
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

const Card=registry.get("indoor-training-central-card");
const view=new Card();
const signal=(state,session)=>view.connectionStatus({
  connected:{state},session_status:{state:session}
});
assert.equal(signal("on","ready").kind,"connected");
assert.equal(signal("on","ready").label,"Ansluten");
assert.equal(signal("on","ready").detail,"Redo");
assert.equal(signal("on","disconnected").detail,"");
assert.equal(signal("off","ready").kind,"disconnected");
assert.equal(signal("off","ready").label,"Frånkopplad");
assert.equal(signal("unavailable","unknown").kind,"unknown");
assert.equal(signal("unknown","unknown").label,"Status okänd");
console.log("Bluetooth connection badge state tests passed");

// Capture controls must be embedded in both new and legacy card constructors.
assert.ok(code.includes('data-capture-action="start"'), "start button missing");
assert.ok(code.includes('data-capture-action="stop"'), "stop button missing");
assert.ok(code.includes('data-capture-action="export"'), "export button missing");
assert.ok(code.includes("homefitnesscode/protocol_capture"), "websocket capture endpoint missing");
assert.ok(code.includes("application/x-ndjson"), "JSONL download missing");
console.log("Protocol Capture UI smoke checks passed");
