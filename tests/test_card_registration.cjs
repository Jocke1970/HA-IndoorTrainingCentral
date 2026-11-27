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


assert.ok(code.includes("homefitnesscode/workouts"), "Workout API missing from dashboard");
assert.ok(code.includes("data-workout-save"), "Manual workout save button missing");
assert.ok(code.includes("workout-history"), "Saved workouts section missing");

// Navigation uses one button per exercise device and live connection status.
// HEADWIND remains a companion, except for an explicitly dedicated fan card.
const connectedGroup=(name,kind,connected,status)=>({
  connected:{state:connected,attributes:{hfc_device_name:name}},
  machine_type:{state:kind},session_status:{state:status}
});
const treadmill=connectedGroup("Q5-6Y 73A9","treadmill","on","ready");
const bike=connectedGroup("Tacx FLUX S","bike","off","disconnected");
const rower=connectedGroup("WP5000","rower","unavailable","unknown");
const fan=connectedGroup("HEADWIND 7185","headwind","on","ready");
assert.equal(view.deviceName(treadmill),"Q5-6Y 73A9");
assert.equal(view.deviceType(treadmill),"treadmill");
assert.equal(view.deviceType(connectedGroup("Q5-6Y 73A9","auto","off","unknown")),"treadmill");
assert.equal(view.deviceType(connectedGroup("Tacx FLUX S","auto","off","unknown")),"bike");
assert.equal(view.deviceType(connectedGroup("WP5000","auto","off","unknown")),"rower");
assert.equal(JSON.stringify(view.visibleDeviceIds({fan,bike,rower,treadmill})),
  JSON.stringify(["treadmill","bike","rower"]));
view.config={entry_id:"fan"};
assert.equal(JSON.stringify(view.visibleDeviceIds({fan,bike,rower,treadmill})),
  JSON.stringify(["fan"]));
view.config={};
assert.equal(JSON.stringify(view.visibleDeviceIds({fan})),JSON.stringify(["fan"]));
assert.equal(view.connectionStatus(treadmill).label,"Ansluten");
assert.equal(view.connectionStatus(bike).label,"Frånkopplad");
assert.equal(view.connectionStatus(rower).label,"Status okänd");
assert.ok(code.includes('data-device-key'),"Device tabs are missing");
assert.ok(code.includes("aria-pressed"),"Device selection should be accessible");
assert.ok(code.includes("device-tab-status-text"),"Status must appear in device buttons");
assert.ok(!code.includes('<select aria-label="Välj träningsmaskin">'),
  "Old training-equipment selector should be removed");
console.log("Device tile navigation and connection status checks passed");


// Q5 reports movement in treadmill-data notifications, not a FTMS running status.
const movingQ5=connectedGroup("Q5-6Y 73A9","treadmill","on","ready");
movingQ5.speed_kmh={state:"3.5"};
assert.equal(view.moving(movingQ5),true);
assert.equal(view.connectionStatus(movingQ5).detail,"Pass pågår");
movingQ5.speed_kmh={state:"0"};
assert.equal(view.moving(movingQ5),false);
assert.equal(view.connectionStatus(movingQ5).detail,"Redo");
movingQ5.speed_kmh={state:"unavailable"};
assert.equal(view.moving(movingQ5),false);
movingQ5.connected.state="off";
movingQ5.speed_kmh={state:"4.0"};
assert.equal(view.moving(movingQ5),false);
assert.equal(view.connectionStatus(movingQ5).kind,"disconnected");
assert.ok(code.includes("data-machine-runner"),"Animated treadmill header runner missing");
assert.ok(code.includes("prefers-reduced-motion"),"Reduced-motion support missing");
assert.ok(code.includes("itc-run"),"Running CSS keyframes missing");
console.log("Treadmill running animation and status fallback tests passed");
