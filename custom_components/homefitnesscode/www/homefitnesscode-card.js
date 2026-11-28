/* HA-IndoorTrainingCentral: responsive Lovelace dashboard with legacy card alias. */
(() => {
  "use strict";
  const defs = {
    treadmill: {name:"Löpband", metrics:["speed_kmh","distance_km","elapsed_s","heart_rate_bpm","incline_percent","energy_kcal"],targets:["speed","incline"]},
    bike: {name:"Cykeltrainer",metrics:["power_w","cadence_rpm","speed_kmh","heart_rate_bpm","distance_km","elapsed_s","resistance_level"],targets:["power","resistance","incline"]},
    rower: {name:"Roddmaskin",metrics:["pace_s_per_500m","stroke_rate_spm","distance_km","stroke_count","elapsed_s","heart_rate_bpm","power_w"],targets:["resistance","power"]},
    heart_rate_monitor: {name:"Pulsband",metrics:[],targets:[]},
    headwind: {name:"Wahoo HEADWIND",metrics:[],targets:[]},
    auto: {name:"Träningsutrustning",metrics:[],targets:[]}
  };
  const label = {speed_kmh:"Hastighet",distance_km:"Distans",elapsed_s:"Tid",heart_rate_bpm:"Puls",
    incline_percent:"Lutning",energy_kcal:"Kalorier",power_w:"Effekt",cadence_rpm:"Kadens",
    resistance_level:"Motstånd",pace_s_per_500m:"Tempo/500 m",stroke_rate_spm:"Roddtag/min",
    stroke_count:"Roddtag",speed:"Hastighet (km/h)",incline:"Lutning/backe (%)",
    power:"ERG-effekt (W)",resistance:"Motstånd"};
  const units={speed_kmh:"km/h",distance_km:"km",heart_rate_bpm:"bpm",incline_percent:"%",
    energy_kcal:"kcal",power_w:"W",cadence_rpm:"rpm",stroke_rate_spm:"spm"};
  const esc=s=>String(s??"").replace(/[&<>"']/g,x=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[x]));
  const invalid=s=>s==null||["unknown","unavailable","none"].includes(s);
  class Card extends HTMLElement {
    setConfig(config){this.config=config||{};this.chosen=this.config.entry_id||null;this.fanSelected=this.config.headwind_entity||null;this.signature="";this.draw();}
    set hass(h){
      this.h=h;this.draw();
      if(Date.now()-(this._lastCapturePoll||0)>5000){
        this._lastCapturePoll=Date.now();
        void this.refreshCapture();
      }
      if(Date.now()-(this._lastWorkoutPoll||0)>5000){
        this._lastWorkoutPoll=Date.now();
        void this.refreshWorkout();
      }
    }
    connectedCallback(){
      if(!this._captureTimer)this._captureTimer=setInterval(()=>{
        void this.refreshCapture();
        void this.refreshWorkout();
      },5000);
    }
    disconnectedCallback(){
      if(this._captureTimer)clearInterval(this._captureTimer);
      this._captureTimer=null;
    }
    getCardSize(){return 6;}
    static getStubConfig(){return {};}
    collect(){
      const groups={};
      for(const [id,s] of Object.entries(this.h.states)){
        const a=s.attributes||{};
        if(!a.hfc_key||!a.hfc_metric)continue;
        (groups[a.hfc_key]??={})[a.hfc_metric]={...s,id};
      }
      return groups;
    }
    fans(){
      return Object.entries(this.h.states).filter(([id,s])=>id.startsWith("fan.")&&
        (s.attributes?.hfc_metric==="headwind_fan"||/headwind/i.test(s.attributes?.friendly_name||id)))
        .sort(([a,sa],[b,sb])=>Number(sb.attributes?.hfc_metric==="headwind_fan")-
          Number(sa.attributes?.hfc_metric==="headwind_fan")||a.localeCompare(b));
    }
    fanEntity(){
      const choices=this.fans();
      const selected=choices.find(([id])=>id===this.fanSelected);
      const g=this.collect()[this.chosen];
      const own=choices.find(([,s])=>s.attributes?.hfc_key&&s.attributes.hfc_key===g?.connected?.attributes?.hfc_key);
      return selected||own||choices[0]||null;
    }
    modeEntity(fan){
      if(!fan)return null;
      const key=fan.attributes?.hfc_key;
      if(!key)return null;
      return Object.entries(this.h.states).find(([id,s])=>id.startsWith("select.")&&
        s.attributes?.hfc_key===key&&s.attributes?.hfc_metric==="headwind_mode_select")||null;
    }
    value(group,key){const s=group[key]?.state;return invalid(s)?null:s;}
    moving(group){
      if(this.deviceType(group)!=="treadmill"||this.value(group,"connected")!=="on")return false;
      if(["paused","stopped","safety_stop","reset"].includes(this.value(group,"session_status")))return false;
      const speed=Number(this.value(group,"speed_kmh"));
      return Number.isFinite(speed)&&speed>0.2;
    }
    connectionStatus(group){
      const connected=this.value(group,"connected");
      if(connected==="on"){
        // Q5 sends treadmill speed but does not always send FTMS status.
        // Display observed movement immediately even if backend status is stale.
        const status=this.moving(group)?"running":this.value(group,"session_status");
        const descriptions={ready:"Redo",running:"Pass pågår",paused:"Pausad",
          stopped:"Stoppad",safety_stop:"Säkerhetsstopp",diagnostic:"Diagnostik",
          disconnected:"",unknown:"",reset:"Återställd"};
        const detail=status&&status in descriptions?descriptions[status]:(status||"");
        return {kind:"connected",label:"Ansluten",detail};
      }
      if(connected==="off")return {kind:"disconnected",label:"Frånkopplad",detail:""};
      return {kind:"unknown",label:"Status okänd",detail:""};
    }
    deviceName(group){
      return Object.values(group||{}).find(s=>s.attributes?.hfc_device_name)?.attributes?.hfc_device_name||"Okänd enhet";
    }
    deviceType(group){
      const raw=this.value(group,"machine_type");
      if(raw&&raw!=="auto"&&defs[raw])return raw;
      const name=this.deviceName(group).toUpperCase();
      if(group?.headwind_fan||name.includes("HEADWIND"))return "headwind";
      if(name.includes("TACX")||name.includes("FLUX"))return "bike";
      if(name.includes("WP5000")||name.includes("RODD"))return "rower";
      if(name.includes("Q5-")||name.includes("LÖPBAND")||
          name.includes("TREADMILL")||name.includes("WALKING PAD"))return "treadmill";
      return "auto";
    }
    visibleDeviceIds(groups){
      const keys=Object.keys(groups);
      const fitness=keys.filter(id=>!["headwind","heart_rate_monitor"].includes(this.deviceType(groups[id])));
      // Existing dedicated HEADWIND dashboards remain selectable.
      const standalone=this.config?.entry_id&&groups[this.config.entry_id]&&
        this.deviceType(groups[this.config.entry_id])==="headwind";
      if(standalone)return [this.config.entry_id];
      const chosen=fitness.length?fitness:keys.filter(id=>this.deviceType(groups[id])!=="heart_rate_monitor");
      const rank={treadmill:0,bike:1,rower:2,auto:3,headwind:4};
      return chosen.sort((a,b)=>
        (rank[this.deviceType(groups[a])]??9)-(rank[this.deviceType(groups[b])]??9)||
        this.deviceName(groups[a]).localeCompare(this.deviceName(groups[b]),"sv"));
    }
    quickTarget(group,kind,direction){
      // Test controls can be used without standing on the belt, but the motor
      // must first be started and live FTMS telemetry must confirm movement.
      if(this.deviceType(group)!=="treadmill"||this.value(group,"connected")!=="on"||
          this.value(group,"armed")!=="on"||!this.moving(group)||
          !["speed","incline"].includes(kind)||![1,-1].includes(direction)||
          ["safety_stop","paused"].includes(this.value(group,"session_status")))return null;
      const entity=group["target_"+kind];
      const sensor=group[kind==="speed"?"speed_kmh":"incline_percent"];
      if(!entity||invalid(entity.state)||!sensor||invalid(sensor.state))return null;
      const current=Number(sensor.state);
      const min=Number(entity.attributes?.min), max=Number(entity.attributes?.max);
      const resolution=Number(entity.attributes?.step);
      const delta=kind==="speed"?0.5:1;
      if(![current,min,max,resolution].every(Number.isFinite)||
          min>max||resolution<=0||resolution>delta+1e-6)return null;
      // For example Q5 can advertise a minimum nonzero treadmill speed.
      // First + from zero must choose that legal minimum, not 0.1 km/h.
      const raw=direction>0?Math.max(current+delta,min):Math.min(current-delta,max);
      if(raw<min-1e-6||raw>max+1e-6)return null;
      const ticks=direction>0?Math.ceil((raw-min)/resolution-1e-6):
        Math.floor((raw-min)/resolution+1e-6);
      const next=Number((min+ticks*resolution).toFixed(4));
      if(next<min-1e-6||next>max+1e-6||
          (direction>0?next<=current+1e-6:next>=current-1e-6))return null;
      return {value:next,entity_id:entity.id};
    }
    display(group,key){
      const raw=this.value(group,key);
      if(raw===null)return "–";
      if(key==="elapsed_s"){
        const s=Math.max(0,Math.floor(Number(raw)||0));
        return [Math.floor(s/3600),Math.floor(s%3600/60),s%60].map(x=>String(x).padStart(2,"0")).join(":");
      }
      if(key==="pace_s_per_500m"){const v=Math.round(Number(raw));return v>0?Math.floor(v/60)+":"+String(v%60).padStart(2,"0"):"–";}
      const n=Number(raw);
      return Number.isFinite(n)?n.toLocaleString("sv-SE",{maximumFractionDigits:2}):raw;
    }
    styleText(){return [
      ":host{display:block;color:var(--primary-text-color);container-type:inline-size}",
      "ha-card{border-radius:16px;overflow:hidden}",
      ".root{padding:20px;display:grid;gap:14px}",
      ".head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}",
      ".device-nav{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,145px),1fr));gap:9px}",
      ".device-tab{display:flex;align-items:flex-start;gap:9px;text-align:left;min-width:0;padding:12px;border:1px solid var(--divider-color);border-radius:11px;background:var(--card-background-color);transition:border-color .15s,background .15s}",
      ".device-tab.is-selected{border:2px solid var(--primary-color);padding:11px;background:color-mix(in srgb,var(--primary-color) 7%,var(--card-background-color))}",
      ".device-tab:focus-visible{outline:2px solid var(--primary-color);outline-offset:2px}",
      ".device-tab-icon{font-size:20px;line-height:1.2;flex:0 0 24px}",
      ".device-tab-body{display:grid;gap:3px;min-width:0;flex:1}",
      ".device-tab-title{font-size:13px;font-weight:700;line-height:1.3}",
      ".device-tab-name{font-size:11px;color:var(--secondary-text-color);overflow-wrap:anywhere;line-height:1.25}",
      ".device-tab-status{display:flex;gap:5px;align-items:center;font-size:11px;color:var(--secondary-text-color);line-height:1.3;flex-wrap:wrap}",
      ".device-tab-status .connection-dot{width:8px;height:8px;flex-basis:8px}",
      ".device-tab-status-text{flex:1;min-width:0}",
      ".kicker{font-weight:750;letter-spacing:.06em;font-size:11px;color:var(--secondary-text-color)}",
      "h2{margin:3px 0;font-size:23px}h3{margin:0 0 8px;font-size:16px}",
      ".machine-heading{display:flex;align-items:center;gap:8px}",
      ".machine-runner{display:inline-block;font-size:21px;line-height:1;transform-origin:center}",
      ".machine-runner.is-moving,.device-tab-icon.is-moving{animation:itc-run .32s ease-in-out infinite alternate}",
      "@keyframes itc-run{0%{transform:translateY(2px) rotate(-18deg)}100%{transform:translateY(-5px) rotate(18deg)}}",
      "@media (prefers-reduced-motion:reduce){.machine-runner.is-moving,.device-tab-icon.is-moving{animation:none;outline:2px solid currentColor;border-radius:4px}}",
      ".sub,.foot{font-size:12px;color:var(--secondary-text-color)}",
      ".connection-status{display:inline-flex;align-items:center;gap:7px;flex-wrap:wrap}",
      ".connection-dot{width:9px;height:9px;display:inline-block;flex:0 0 9px;border-radius:50%;background:var(--secondary-text-color);opacity:.8}",
      ".connection-dot.is-connected{background:var(--success-color,#2e9d58);opacity:1;box-shadow:0 0 0 2px color-mix(in srgb,var(--success-color,#2e9d58) 18%,transparent)}",
      ".connection-dot.is-disconnected{background:var(--secondary-text-color);opacity:.6}",
      ".connection-dot.is-unknown{background:var(--warning-color,#e7a12a);opacity:1}",
      ".connection-detail:not(:empty)::before{content:'·';margin-right:7px;color:var(--secondary-text-color)}",
      "select,input{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:9px;padding:9px;box-sizing:border-box;min-width:0}",
      ".stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,145px),1fr));gap:9px}",
      ".tile{padding:12px;border-radius:12px;background:var(--secondary-background-color)}",
      ".label{font-size:12px;color:var(--secondary-text-color)}",
      ".val{font-size:26px;font-weight:750;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".unit{font-size:11px;color:var(--secondary-text-color)}",
      ".panel{border:1px solid var(--divider-color);padding:14px;border-radius:12px}",
      ".capture summary,.workout summary{cursor:pointer;font-size:14px;font-weight:650}",
      ".workout-content{display:grid;gap:12px;margin-top:12px}",
      ".workout-history{display:grid;gap:8px}",
      ".workout-row{border:1px solid var(--divider-color);border-radius:8px;padding:10px;font-size:12px}",
      ".workout-row strong{display:block;font-size:13px;margin-bottom:3px}",
      ".workout-note{font-size:12px;color:var(--secondary-text-color);overflow-wrap:anywhere}",
      ".capture summary:focus-visible{outline:2px solid var(--primary-color);outline-offset:3px}",
      ".capture-content{display:grid;gap:10px;margin-top:12px}",
      ".capture-detail{font-size:12px;color:var(--secondary-text-color)}",
      ".capture .actions button{flex:1 1 140px}",
      ".actions,.targetrow{display:flex;gap:8px;flex-wrap:wrap}",
      "button{font:inherit;font-size:13px;cursor:pointer;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:9px;padding:10px}",
      "button:disabled,input:disabled{opacity:.4;cursor:not-allowed}",
      ".danger{color:var(--error-color);border-color:var(--error-color)}",
      ".controls{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,220px),1fr));gap:12px;margin-top:15px}",
      ".target{display:grid;gap:6px;font-size:12px}",
      ".targetrow input{flex:1 1 100px;width:80px;min-width:0}",
      ".ftms-test{display:grid;gap:12px;margin-top:12px}",
      ".ftms-transport{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}",
      ".ftms-transport button{min-width:0;min-height:44px;font-weight:650}",
      ".ftms-step-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}",
      ".ftms-step-box{border:1px solid var(--divider-color);border-radius:11px;padding:12px;display:grid;gap:8px;min-width:0}",
      ".ftms-step-title{font-size:13px;font-weight:650}",
      ".ftms-step-values{font-size:11px;color:var(--secondary-text-color)}",
      ".ftms-step-actions{display:grid;grid-template-columns:minmax(0,1fr) minmax(65px,1.7fr) minmax(0,1fr);align-items:center;gap:7px}",
      ".ftms-step-actions button{font-size:22px;font-weight:750;min-width:0;min-height:48px}",
      ".ftms-step-display{text-align:center;font-size:12px;white-space:nowrap;min-width:0}",
      ".ftms-step-box [data-step-value]{font-size:20px;font-weight:700;color:var(--primary-text-color)}",
      ".ftms-lock{font-size:12px;color:var(--secondary-text-color);font-weight:600}",
      ".ftms-advanced{margin-top:5px;border-top:1px solid var(--divider-color);padding-top:10px}",
      ".ftms-advanced summary{cursor:pointer;font-size:12px;font-weight:650}",
      ".ftms-note{font-size:12px;color:var(--secondary-text-color)}",
      ".note,.message{margin:8px 0;font-size:12px;color:var(--secondary-text-color)}",
      ".foot{display:flex;justify-content:space-between;gap:12px}",
      ".fan-line{display:flex;align-items:center;gap:12px;flex-wrap:wrap}",
      ".fan-percent{font-size:23px;font-weight:750}",
      ".fan-line select{max-width:210px;flex:1 1 150px}",
      ".fan-note{font-size:12px;color:var(--secondary-text-color);margin:4px 0}",
      "@container (max-width:540px){.root{padding:12px}.head{display:grid;gap:10px}.device-nav{grid-template-columns:repeat(2,minmax(0,1fr))}.device-tab{padding:10px;gap:6px}.device-tab.is-selected{padding:9px}.device-tab-icon{font-size:18px;flex-basis:20px}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.val{font-size:22px}.controls{grid-template-columns:1fr}.actions button{flex:1}}",
      "@container (max-width:400px){.ftms-step-grid{grid-template-columns:1fr}}",
      "@container (max-width:300px){.device-nav{grid-template-columns:1fr}.ftms-transport{grid-template-columns:1fr}}"
    ].join("");}
    shell(key,type,groups){
      const d=defs[type]||defs.auto;
      const icons={treadmill:"🏃",bike:"🚴",rower:"🚣",auto:"🏋️",headwind:"💨"};
      const tabs=this.visibleDeviceIds(groups).map(id=>{
        const group=groups[id],kind=this.deviceType(group),conn=this.connectionStatus(group);
        const title=defs[kind]?.name||defs.auto.name;
        return '<button type="button" class="device-tab'+(id===key?' is-selected':'')+
          '" data-device-key="'+esc(id)+'" aria-pressed="'+(id===key?'true':'false')+
          '" aria-label="'+esc(title+": "+this.deviceName(group)+", "+conn.label+(conn.detail?", "+conn.detail:""))+'">'+
          '<span class="device-tab-icon'+(this.moving(group)?' is-moving':'')+
          '" aria-hidden="true">'+icons[kind]+'</span>'+
          '<span class="device-tab-body"><span class="device-tab-title">'+esc(title)+'</span>'+
          '<span class="device-tab-name">'+esc(this.deviceName(group))+'</span>'+
          '<span class="device-tab-status"><span class="connection-dot is-'+conn.kind+
          '" aria-hidden="true"></span><span class="device-tab-status-text">'+
          esc(conn.label+(conn.detail?" · "+conn.detail:""))+
          '</span></span></span></button>';
      }).join("");
      const tiles=d.metrics.map(m=>'<div class="tile"><div class="label">'+esc(label[m]||m)+'</div><div class="val" data-metric="'+m+'">–</div><div class="unit">'+esc(units[m]||"")+'</div></div>').join("");
      const targets=d.targets.filter(m=>groups[key]?.["target_"+m]).map(m=>'<label class="target">'+esc(label[m])+'<span class="targetrow"><input type="number" inputmode="decimal" data-target="'+m+'"/><button type="button" data-set="'+m+'">Ställ in</button></span></label>').join("");
      const actions=['arm',...(type==='treadmill'?[]:[])].filter(a=>groups[key]?.[a]).map(a=>
        '<button type="button" data-action="'+a+'" '+(a==='stop'?'class="danger"':'')+'>'+({arm:type==="bike"?"Aktivera trainerstyrning":"Aktivera styrning",start:"Start",pause:"Paus",stop:"Stopp"}[a])+'</button>').join("");
      const ftmsTest=type==="treadmill"?(
        '<div class="ftms-test"><div class="ftms-transport">'+
        '<button type="button" data-action="pause" data-ftms-transport>Ⅱ Paus</button>'+
        '<button type="button" class="danger" data-action="stop" data-ftms-transport>■ Stopp</button></div>'+
        '<div class="ftms-step-grid">'+
        '<div class="ftms-step-box"><div class="ftms-step-title">Hastighet</div>'+
        '<div class="ftms-step-values">Steg: 0,5 km/h</div>'+
        '<div class="ftms-step-actions"><button type="button" data-step-kind="speed" data-step-direction="-1" disabled aria-label="Minska hastighet med 0,5 km/h">−</button>'+
        '<span class="ftms-step-display"><span data-step-value="speed">–</span> km/h</span>'+
        '<button type="button" data-step-kind="speed" data-step-direction="1" disabled aria-label="Öka hastighet med 0,5 km/h">+</button></div></div>'+
        '<div class="ftms-step-box"><div class="ftms-step-title">Lutning</div>'+
        '<div class="ftms-step-values">Steg: 1 procentenhet</div>'+
        '<div class="ftms-step-actions"><button type="button" data-step-kind="incline" data-step-direction="-1" disabled aria-label="Minska lutningen med 1 procentenhet">−</button>'+
        '<span class="ftms-step-display"><span data-step-value="incline">–</span> %</span>'+
        '<button type="button" data-step-kind="incline" data-step-direction="1" disabled aria-label="Öka lutningen med 1 procentenhet">+</button></div></div></div>'+
        '<div class="ftms-lock" data-ftms-lock>Starta bandet på löpbandets konsol och aktivera styrning.</div>'+
        '<p class="ftms-note">Start och återstart sker endast på löpbandets konsol. När Q5 rapporterar rörelse går det att ändra hastighet och lutning direkt med ±, utan bekräftelser. Stopp är inte ett nödstopp; använd säkerhetsnyckeln vid fara.</p>'+
        '<details class="ftms-advanced"><summary>Avancerat · exakta FTMS-målvärden</summary>'+
        '<div class="controls">'+targets+'</div></details></div>'):"";
      const fanChoices=this.fans();
      const fanOptions=fanChoices.map(([id,s])=>'<option value="'+esc(id)+'"'+(this.fanSelected===id?' selected':'')+'>'+esc(s.attributes?.friendly_name||id)+'</option>').join("");
      const fanPanel=(type==="bike"||type==="headwind")?(
        '<section class="panel" data-fan><h3>💨 Wahoo HEADWIND</h3>'+
        (fanChoices.length?
          '<div class="fan-line"><select data-fan-choice aria-label="Välj fläkt">'+fanOptions+'</select><span class="fan-percent" data-fan-percent>–</span><span class="connection-status"><span class="connection-dot is-unknown" data-fan-dot aria-hidden="true"></span><span data-fan-status>Okänd</span></span></div>'+
          '<div class="controls"><label class="target">Driftläge<select data-fan-mode><option value="off">Av</option><option value="manual">Manuell</option><option value="heart_rate">Puls (sensor i fläkten)</option><option value="speed">Hastighet (sensor i fläkten)</option></select></label>'+
          '<label class="target">Fläkthastighet (%)<span class="targetrow"><input data-fan-target type="number" min="0" max="100" step="5" inputmode="numeric" placeholder="0–100"/><button type="button" data-fan-apply>Ställ in</button></span></label></div>'+
          '<div class="actions"><button data-fan-preset="0" type="button">Av</button><button data-fan-preset="25" type="button">25 %</button><button data-fan-preset="50" type="button">50 %</button><button data-fan-preset="75" type="button">75 %</button><button data-fan-preset="100" type="button">100 %</button></div>'+
          '<p class="fan-note">Pulsstyrning via ditt parkopplade pulsband är huvudläge. HA ändrar inte fläktläget automatiskt. Effektstyrning/adaptiv kylning kräver nyare firmware och konfigureras i Wahoo-appen.</p><p class="fan-note" data-fan-fw>Firmware: okänd</p>'
          :'<p class="fan-note">Lägg till Wahoo HEADWIND som enhet i HomeFitnessCode för gemensam visning och styrning.</p>')+
        '</section>'
      ):"";
      const workoutPanel=type==="treadmill"?
        '<details class="panel workout" data-workout><summary>🏃 Träningspass</summary>'+
        '<div class="workout-content"><div class="workout-note" data-workout-status>Hämtar passinformation…</div>'+
        '<div class="actions"><button type="button" data-workout-save disabled>Avsluta och spara pass</button></div>'+
        '<label class="workout-note">FIT-exportprofil <select data-fit-profile><option value="native">HA-ITC Native</option><option value="fenix7pro">Garmin fēnix 7 Pro</option></select></label>'+ 
        '<p class="workout-note">JSONL behålls under betafasen.</p>'+
        '<div class="workout-history" data-workout-history></div>'+
        '<div class="workout-note" data-workout-path></div>'+
        '<p class="workout-note">Automatisk inspelning när bandet börjar röra sig. Rå FTMS-data sparas som JSONL på HA-servern, och slutvärden beräknas från filen. Du behöver inte aktivera Protocol Capture.</p>'+
        '</div></details>':"";
      const capturePanel='<details class="panel capture" data-capture><summary>🔍 Protocol Capture</summary>'+
        '<div class="capture-content"><p class="note">Manuell rådatainspelning för analys (högst 10 minuter, 3 000 paket eller 750 kB). Ingen påverkan på maskinens styrning.</p>'+
        '<div class="capture-detail" data-capture-status role="status" aria-live="polite">Hämtar status…</div>'+
        '<div class="actions"><button type="button" data-capture-action="start">Starta inspelning</button>'+
        '<button type="button" data-capture-action="stop" disabled>Stoppa</button>'+
        '<button type="button" data-capture-action="export" disabled>Exportera JSONL</button></div>'+
        '<p class="capture-detail">Inspelningen hålls tillfälligt i HA-minnet. Exportera innan integrationen startas om. Endast administratörer kan använda funktionen.</p></div></details>';
      const trainPanel=(type==="headwind"||type==="auto")?"":(
        '<section class="stats">'+tiles+'</section><section class="panel"><h3>Styrning</h3>'+
        '<p class="note">Manuell aktivering krävs. Ingen automatisk start efter återanslutning.</p>'+
        '<div class="actions">'+actions+'</div>'+
        (type==="treadmill"?ftmsTest:'<div class="controls">'+targets+'</div>')+
        '<div class="message" aria-live="polite"></div></section>'
      );
      this.shadowRoot.innerHTML='<style>'+this.styleText()+'</style><ha-card><div class="root">'+
        '<header class="head"><div><div class="kicker">HA-INDOORTRAININGCENTRAL</div>'+
        '<h2 class="machine-heading">'+(type==="treadmill"?'<span class="machine-runner" data-machine-runner aria-hidden="true">🏃</span>':"")+
        esc(d.name)+'</h2></div></header>'+
        '<nav class="device-nav" aria-label="Välj träningsmaskin">'+tabs+'</nav>'+
        '<section><h3>♥ Pulskälla</h3><select data-hr-source aria-label="Pulskälla"></select><div data-hr-reading aria-live="polite">– bpm</div></section>'+
        trainPanel+fanPanel+workoutPanel+capturePanel+
        '<footer class="foot"><span data-protocol>Protokoll: –</span><span data-arm>Låst</span></footer>'+
        '</div></ha-card>';
      this.shadowRoot.querySelectorAll('[data-device-key]').forEach(button=>button.addEventListener('click',()=>{
        const id=button.dataset.deviceKey;
        if(!groups[id]||id===this.chosen)return;
        this.chosen=id;
        this.signature="";
        this.draw();
        void this.refreshWorkout();
        void this.refreshCapture();
      }));
      this.shadowRoot.querySelector("[data-hr-source]")?.addEventListener("change",e=>{const source=e.target.value;const key=this.chosen;if(this.deviceType(this.collect()[key])==="treadmill"){this.h.callWS({type:"homefitnesscode/workouts",entry_id:key,action:"hr_source",hr_source:source}).then(()=>{this.hrSource=source;this.draw();}).catch(err=>{this.message(err?.message||String(err));this.draw();});}else{this.hrSource=source;this.draw();}});
      this.shadowRoot.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>this.action(b.dataset.action)));
      this.shadowRoot.querySelectorAll('[data-set]').forEach(b=>b.addEventListener('click',()=>this.setTarget(b.dataset.set)));
      this.shadowRoot.querySelectorAll('[data-step-kind]').forEach(b=>
        b.addEventListener('click',()=>this.incrementTarget(b.dataset.stepKind,Number(b.dataset.stepDirection))));
      this.shadowRoot.querySelector('[data-fan-choice]')?.addEventListener('change',e=>{this.fanSelected=e.target.value;this.signature="";this.draw();});
      this.shadowRoot.querySelector('[data-fan-mode]')?.addEventListener('change',e=>this.fanMode(e.target.value));
      this.shadowRoot.querySelector('[data-fan-apply]')?.addEventListener('click',()=>{
        const input=this.shadowRoot.querySelector('[data-fan-target]');
        if(input.value.trim()!==""&&input.checkValidity())this.fanPercent(Number(input.value));
      });
      this.shadowRoot.querySelectorAll('[data-fan-preset]').forEach(b=>b.addEventListener('click',()=>this.fanPercent(Number(b.dataset.fanPreset))));
      this.shadowRoot.querySelectorAll('[data-capture-action]').forEach(b=>
        b.addEventListener('click',()=>this.captureAction(b.dataset.captureAction)));
      this.shadowRoot.querySelector('[data-workout-save]')?.addEventListener('click',()=>this.saveWorkout());
      this.shadowRoot.querySelector('[data-fit-profile]')?.addEventListener('change',e=>this.updateWorkout("fit_settings",{profile:e.target.value}));
      this.paintCapture();
      this.paintWorkout();
      this.signature=key+':'+type+':'+this.visibleDeviceIds(groups).join(',')+':'+Object.keys(groups[key]).sort().join(',')+':'+this.fans().map(([id])=>id).join(',');
    }
    draw(){
      if(!this.h)return;
      if(!this.shadowRoot)this.attachShadow({mode:"open"});
      const groups=this.collect(),ids=this.visibleDeviceIds(groups);
      if(!ids.length){this.shadowRoot.innerHTML='<ha-card><div style="padding:22px">Inga maskiner registrerade. Konfigurera HA-IndoorTrainingCentral först.</div></ha-card>';this.signature="";return;}
      const key=ids.includes(this.chosen)?this.chosen:ids[0];this.chosen=key;
      const g=groups[key];
      const type=this.deviceType(g);
      if(this.signature!==key+':'+type+':'+ids.join(',')+':'+Object.keys(g).sort().join(',')+':'+this.fans().map(([id])=>id).join(','))this.shell(key,type,groups);
      const connection=this.connectionStatus(g);
      const connected=connection.kind==="connected",armed=this.value(g,"armed")==="on";
      for(const button of this.shadowRoot.querySelectorAll('[data-device-key]')){
        const group=groups[button.dataset.deviceKey];
        if(!group)continue;
        const status=this.connectionStatus(group);
        button.classList.toggle("is-selected",button.dataset.deviceKey===key);
        button.setAttribute("aria-pressed",button.dataset.deviceKey===key?"true":"false");
        button.setAttribute("aria-label", (defs[this.deviceType(group)]?.name||defs.auto.name)+
          ": "+this.deviceName(group)+", "+status.label+
          (status.detail?", "+status.detail:""));
        button.querySelector(".connection-dot").className="connection-dot is-"+status.kind;
        button.querySelector(".device-tab-icon")?.classList.toggle("is-moving",this.moving(group));
        button.querySelector(".device-tab-status-text").textContent=
          status.label+(status.detail?" · "+status.detail:"");
      }
      this.shadowRoot.querySelector('[data-machine-runner]')?.classList.toggle("is-moving",this.moving(g));
      this.shadowRoot.querySelector('[data-protocol]').textContent="Protokoll: "+(this.value(g,"protocol")||"–");
      this.shadowRoot.querySelector('[data-arm]').textContent=type==="headwind"?"Fläktstyrning separat":(armed?"Styrning aktiverad":"Styrning låst");
      const hrSelect=this.shadowRoot.querySelector("[data-hr-source]");
      const hrBands=Object.entries(groups).filter(([,v])=>this.deviceType(v)==="heart_rate_monitor");
      if(hrSelect){
        const options='<option value="">Träningsmaskinen</option>'+hrBands.map(([id,v])=>'<option value="'+esc(id)+'">'+esc(this.deviceName(v))+'</option>').join("");
        if(hrSelect._options!==options){hrSelect.innerHTML=options;hrSelect._options=options;}
        const workout=this._workoutStates?.[key];
        hrSelect.disabled=type==="treadmill"&&!!workout?.active;
        hrSelect.value=hrSelect.disabled?(workout.hr_source_id||""):(this.hrSource??hrBands[0]?.[0]??"");
        const source=hrSelect.value?groups[hrSelect.value]:g;
        const pulse=source&&this.value(source,"connected")==="on"?this.display(source,"heart_rate_bpm"):"–";
        const battery=source&&this.value(source,"connected")==="on"?this.display(source,"battery_percent"):"–";
        this.shadowRoot.querySelector("[data-hr-reading]").textContent=pulse+" bpm"+(hrSelect.value?" · Batteri "+battery+(battery==="–"?"":" %"):"");
        this.shadowRoot.querySelectorAll('[data-metric="heart_rate_bpm"]').forEach(el=>el.textContent=pulse);
      }
      this.shadowRoot.querySelectorAll('[data-metric]:not([data-metric="heart_rate_bpm"])').forEach(el=>el.textContent=this.display(g,el.dataset.metric));
      this.shadowRoot.querySelectorAll('[data-action]').forEach(b=>{
        const e=g[b.dataset.action];
        b.disabled=!connected||!e||e.state==="unavailable"||
          (b.dataset.action!=="arm"&&!armed);
      });
      this.shadowRoot.querySelectorAll('[data-step-value]').forEach(el=>
        el.textContent=this.display(g,el.dataset.stepValue==="speed"?"speed_kmh":"incline_percent"));
      const lock=this.shadowRoot.querySelector('[data-ftms-lock]');
      if(lock)lock.textContent=!connected?"Bluetooth frånkopplat – inga FTMS-kommandon möjliga.":
        !armed?"Aktivera styrning. Start sker endast på löpbandet.":
        this.moving(g)?"Bandet rör sig – hastighet och lutning kan ändras med ±.":
        "Starta bandet först på konsolen – ± aktiveras när Q5 rapporterar rörelse.";
      this.shadowRoot.querySelectorAll('[data-step-kind]').forEach(button=>{
        const cmd=this.quickTarget(g,button.dataset.stepKind,Number(button.dataset.stepDirection));
        button.disabled=!cmd||!!this._stepBusy;
        button.title=cmd?"Målvärde: "+cmd.value+(button.dataset.stepKind==="speed"?" km/h":" %"):
          "Starta bandet först. Styrning måste vara aktiv och värdet inom FTMS-gränserna.";
      });
      this.refreshFan(type);
      this.paintCapture();
      this.paintWorkout();
      this.shadowRoot.querySelectorAll('[data-target]').forEach(input=>{
        const e=g["target_"+input.dataset.target];
        input.disabled=!connected||!armed||
          (type==="treadmill"&&!this.moving(g))||
          !e||e.state==="unavailable";
        if(e){
          for(const k of ["min","max","step"])if(e.attributes[k]!==undefined)input[k]=e.attributes[k];
          if(this.shadowRoot.activeElement!==input&&e.state!=="unavailable")input.placeholder=e.state;
        }
        this.shadowRoot.querySelector('[data-set="'+input.dataset.target+'"]').disabled=input.disabled;
      });
    }
    refreshFan(type){
      if(type!=="bike"&&type!=="headwind")return;
      const item=this.fanEntity(), fan=item?.[1], mode=this.modeEntity(fan);
      const e=this.shadowRoot.querySelector('[data-fan-percent]');
      if(!e)return;
      const available=!!fan&&!invalid(fan.state);
      const reported=fan?.attributes?.percentage;
      const pct=(reported===undefined||reported===null)?NaN:Number(reported);
      const value=Number.isFinite(pct)?pct:null;
      e.textContent=value!==null&&available?value+" %":"–";
      const status=this.shadowRoot.querySelector('[data-fan-status]');
      const fanConnected=available&&this.value(this.collect()[fan?.attributes?.hfc_key]||{},"connected")==="on";
      status.textContent=fanConnected?"Ansluten":(available?"Status okänd":"Frånkopplad");
      this.shadowRoot.querySelector('[data-fan-dot]').className=
        "connection-dot is-"+(fanConnected?"connected":available?"unknown":"disconnected");
      const fwNode=this.shadowRoot.querySelector('[data-fan-fw]');
      if(fwNode){
        const key=fan.attributes?.hfc_key;
        const fw=Object.values(this.h.states).find(s=>s.attributes?.hfc_key===key&&s.attributes?.hfc_metric==="firmware_version");
        fwNode.textContent="Firmware: "+(fw&&!invalid(fw.state)?fw.state:"ej avläst");
      }
      const sel=this.shadowRoot.querySelector('[data-fan-mode]');
      sel.disabled=!available||!mode||invalid(mode[1].state);
      if(mode&&!invalid(mode[1].state))sel.value=mode[1].state;
      const speed=this.shadowRoot.querySelector('[data-fan-target]');
      speed.disabled=!available;
      speed.placeholder=value!==null&&available?String(value):"0–100";
      this.shadowRoot.querySelector('[data-fan-apply]').disabled=!available;
      this.shadowRoot.querySelectorAll('[data-fan-preset]').forEach(btn=>btn.disabled=!available);
    }
    paintWorkout(){
      const node=this.shadowRoot?.querySelector('[data-workout-status]');
      if(!node)return;
      const s=this._workoutStates?.[this.chosen];
      const err=this._workoutErrors?.[this.chosen];
      const busy=this._workoutBusy===this.chosen;
      if(err)node.textContent="Fel vid passhämtning: "+err;
      else if(!s)node.textContent="Hämtar passinformation…";
      else if(s.paused)node.textContent="⏸ Pausat · återupptas när bandet rör sig";
      else if(s.active)node.textContent="● Spelar in · "+s.elapsed_s+
        " s · "+(s.current_met!=null?Number(s.current_met).toFixed(1)+" MET · ":"")+Number(s.distance_km||0).toLocaleString("sv-SE",{maximumFractionDigits:3})+
        " km · cirka "+Math.ceil((s.raw_bytes||0)/1024)+" kB rådata";
      else if(s.saving)node.textContent="Sparar pass och läser tillbaka rådata…";
      else node.textContent="Redo. Inspelning startar automatiskt när löpbandet rör sig.";
      let dialog=this.shadowRoot.querySelector('[data-pause-dialog]');
      if(s?.pause_pending&&!dialog){
        dialog=document.createElement("dialog");
        dialog.dataset.pauseDialog="";
        dialog.innerHTML='<h3>Träningspass pausat</h3><p>Löpbandet har stått stilla i 15 sekunder. Vill du fortsätta senare?</p><div class="actions"><button data-keep>Behåll pausat</button><button data-finish>Avsluta och spara</button></div>';
        node.parentNode.append(dialog);
        dialog.addEventListener("cancel",e=>e.preventDefault());
        dialog.querySelector("[data-keep]").onclick=()=>this.updateWorkout("keep_paused",{});
        dialog.querySelector("[data-finish]").onclick=()=>this.updateWorkout("save",{});
        dialog.showModal();
      }else if(!s?.pause_pending&&dialog){dialog.close();dialog.remove();}
      const btn=this.shadowRoot.querySelector('[data-workout-save]');
      if(btn)btn.disabled=busy||!s?.active;
      const profile=this.shadowRoot.querySelector('[data-fit-profile]');
      if(profile){profile.value=s?.fit_profile||"native";profile.disabled=busy||!s;}
      const history=this.shadowRoot.querySelector('[data-workout-history]');
      if(history){
        const sessions=s?.recent||[];
        history.innerHTML=sessions.length?sessions.slice(0,5).map(x=>{
          const date=x.started_at?new Date(x.started_at).toLocaleString("sv-SE"):"Okänt datum";
          const seconds=Math.max(0,Math.round(Number(x.elapsed_s)||0));
          const duration=[Math.floor(seconds/3600),Math.floor((seconds%3600)/60),
            seconds%60].map(n=>String(n).padStart(2,"0")).join(":");
          const distance=Number(x.distance_km||0).toLocaleString("sv-SE",
            {minimumFractionDigits:2,maximumFractionDigits:3});
          return '<div class="workout-row"><strong>'+esc(x.session_name||"Löpband")+' · '+esc(date)+
            (x.complete?' · Sparat':' · Återställt efter avbrott')+'</strong>'+
            esc(duration)+' · '+esc(distance)+' km · '+esc(x.energy_kcal||0)+
            ' kcal · '+(x.heart_rate_samples?'Puls '+esc(x.average_heart_rate_bpm)+' / max '+esc(x.max_heart_rate_bpm)+' bpm · ':'')+esc(x.raw_frames||0)+' datapaket'+(x.average_met!=null?' · MET '+esc(x.average_met)+' / max '+esc(x.max_met)+' · '+esc(x.met_minutes)+' MET-min':'')+(x.complete?'<div class="actions"><button type="button" data-fit-id="'+esc(x.id)+'">Hämta FIT</button><button type="button" data-rename-id="'+esc(x.id)+'">Byt namn</button></div>':'')+'</div>';
        }).join(""):'<div class="workout-note">Inga sparade pass ännu.</div>';
        history.querySelectorAll('[data-fit-id]').forEach(b=>b.addEventListener('click',()=>this.downloadFit(b.dataset.fitId)));
        history.querySelectorAll('[data-rename-id]').forEach(b=>b.addEventListener('click',()=>{
          const id=b.dataset.renameId;
          const name=prompt("Passnamn",sessions.find(x=>x.id===id)?.session_name||"Löpband");
          if(name!==null)this.updateWorkout("rename",{session_id:id,name});
        }));
      }
      const path=this.shadowRoot.querySelector('[data-workout-path]');
      if(path)path.textContent=s?.storage_directory?
        'Lagring på HA: '+s.storage_directory+' (FIT + rådata .jsonl + .summary.json)':'';
    }
    async updateWorkout(action,extra){
      const key=this.chosen;
      if(!key||this._workoutBusy)return;
      this._workoutBusy=key;
      try{
        const result=await this.h.callWS({type:"homefitnesscode/workouts",entry_id:key,action,...extra});
        (this._workoutStates??={})[key]=result;
        if(this._workoutErrors)delete this._workoutErrors[key];
      }catch(err){
        (this._workoutErrors??={})[key]=err?.message||String(err);
      }finally{
        this._workoutBusy=null;
        if(this.chosen===key)this.paintWorkout();
      }
    }
    async downloadFit(id){
      const key=this.chosen;
      if(!key||this._workoutBusy)return;
      const state=this._workoutStates?.[key];
      const session=state?.recent?.find(x=>x.id===id);
      const profile=session?.raw_available===false?(session.fit_profile||"native"):(state?.fit_profile||"native");
      this._workoutBusy=key;
      try{
        const result=await this.h.callWS({type:"homefitnesscode/workouts",entry_id:key,
          action:"fit_download",session_id:id,profile});
        const bytes=Uint8Array.from(atob(result.base64),c=>c.charCodeAt(0));
        const url=URL.createObjectURL(new Blob([bytes],{type:"application/octet-stream"}));
        const a=document.createElement("a");
        a.href=url;a.download=result.filename;a.click();
        setTimeout(()=>URL.revokeObjectURL(url),1000);
      }catch(err){
        (this._workoutErrors??={})[key]=err?.message||String(err);
      }finally{
        this._workoutBusy=null;
        if(this.chosen===key)this.paintWorkout();
      }
    }
    async refreshWorkout(){
      if(!this.h?.callWS||!this.chosen||this._workoutBusy||this._workoutPolling)return;
      const key=this.chosen;
      this._workoutPolling=true;
      try{
        const result=await this.h.callWS({type:"homefitnesscode/workouts",
          entry_id:key,action:"status"});
        (this._workoutStates??={})[key]=result;
        if(this._workoutErrors)delete this._workoutErrors[key];
      }catch(err){
        (this._workoutErrors??={})[key]=err?.message||String(err);
      }finally{
        this._workoutPolling=false;
        if(this.chosen===key)this.paintWorkout();
      }
    }
    async saveWorkout(){
      const key=this.chosen;
      if(!this.h?.callWS||!key||this._workoutBusy||!this._workoutStates?.[key]?.active)return;
      if(!confirm("Avsluta inspelningen och spara passet från rådata? Löpbandet fortsätter köras tills du stoppar det på konsolen."))return;
      this._workoutBusy=key;
      this.paintWorkout();
      try{
        const result=await this.h.callWS({type:"homefitnesscode/workouts",
          entry_id:key,action:"save"});
        (this._workoutStates??={})[key]=result;
        if(this._workoutErrors)delete this._workoutErrors[key];
      }catch(err){
        (this._workoutErrors??={})[key]=err?.message||String(err);
      }finally{
        this._workoutBusy=null;
        if(this.chosen===key)this.paintWorkout();
      }
    }
    paintCapture(){
      if(!this.shadowRoot)return;
      const statusNode=this.shadowRoot.querySelector('[data-capture-status]');
      if(!statusNode)return;
      const s=this._captureStates?.[this.chosen];
      const error=this._captureErrors?.[this.chosen];
      const busy=this._captureBusy===this.chosen;
      if(error)statusNode.textContent="Fel: "+error;
      else if(!s)statusNode.textContent="Hämtar status…";
      else if(s.active)statusNode.textContent="● Spelar in · "+s.count+
        " paket · "+Math.ceil(s.bytes/1024)+" kB · upp till "+s.seconds_remaining+" s kvar";
      else if(s.started_at)statusNode.textContent="Stoppad ("+
        ({manual:"manuellt",timeout:"tidsgräns",record_limit:"paketgräns",
          byte_limit:"storleksgräns",unload:"avslutad"}[s.stop_reason]||"klar")+
        ") · "+s.count+" paket · "+Math.ceil(s.bytes/1024)+" kB";
      else statusNode.textContent="Ingen inspelning startad";
      for(const action of ["start","stop","export"]){
        const btn=this.shadowRoot.querySelector('[data-capture-action="'+action+'"]');
        if(btn)btn.disabled=busy||(action==="start"?!!s?.active:
          action==="stop"?!s?.active:!s?.count);
      }
    }
    async refreshCapture(){
      if(!this.h?.callWS||!this.chosen||this._captureBusy||this._capturePolling)return;
      const key=this.chosen;
      this._capturePolling=true;
      try{
        const result=await this.h.callWS({type:"homefitnesscode/protocol_capture",
          entry_id:key,action:"status"});
        (this._captureStates??={})[key]=result;
        if(this._captureErrors)delete this._captureErrors[key];
      }catch(err){
        (this._captureErrors??={})[key]=err?.message||String(err);
      }finally{
        this._capturePolling=false;
        if(this.chosen===key)this.paintCapture();
      }
    }
    async captureAction(action){
      const key=this.chosen;
      if(!this.h?.callWS||!key||this._captureBusy)return;
      const prev=this._captureStates?.[key];
      if(action==="start"&&prev?.count&&!prev.active&&
        !confirm("En ny inspelning ersätter den tidigare. Fortsätta?"))return;
      this._captureBusy=key;
      this.paintCapture();
      try{
        const result=await this.h.callWS({type:"homefitnesscode/protocol_capture",
          entry_id:key,action});
        (this._captureStates??={})[key]=result.status||result;
        if(this._captureErrors)delete this._captureErrors[key];
        if(action==="export"){
          if(!result.jsonl)throw new Error("Det finns ingen inspelning att exportera.");
          const blob=new Blob([result.jsonl],{type:"application/x-ndjson;charset=utf-8"});
          const url=URL.createObjectURL(blob),a=document.createElement("a");
          a.href=url;
          a.download="itc-protocol-"+new Date().toISOString().replace(/[:.]/g,"-")+".jsonl";
          document.body.appendChild(a);a.click();a.remove();
          setTimeout(()=>URL.revokeObjectURL(url),1000);
        }
      }catch(err){
        (this._captureErrors??={})[key]=err?.message||String(err);
      }finally{
        this._captureBusy=null;
        if(this.chosen===key)this.paintCapture();
      }
    }
    async fanMode(mode){
      const item=this.fanEntity(), selector=this.modeEntity(item?.[1]);
      if(!selector||invalid(selector[1].state))return;
      await this.call("select","select_option",{entity_id:selector[0],option:mode});
    }
    async fanPercent(percent){
      const item=this.fanEntity(), fan=item?.[1];
      if(!item||invalid(fan.state)||!Number.isInteger(percent)||percent<0||percent>100)return;
      if(percent===0)await this.call("fan","turn_off",{entity_id:item[0]});
      else await this.call("fan","set_percentage",{entity_id:item[0],percentage:percent});
    }
    async action(name){
      const g=this.collect()[this.chosen],entry=g?.[name];
      if(!entry||entry.state==="unavailable")return;
      if(name==="start")return;
      await this.call("button","press",{entity_id:entry.id});
    }
    async incrementTarget(kind,direction){
      if(this._stepBusy||!this.h?.callService)return;
      const key=this.chosen;
      const group=this.collect()[key];
      const command=this.quickTarget(group,kind,direction);
      if(!command){this.message("Ingen giltig FTMS-ändring möjlig just nu.");return;}
      // Only a connected, armed and moving treadmill allows +/- targets.
      // No repeated confirmation dialogs once movement is confirmed.
      this._stepBusy=true;
      this.draw();
      try{
        await this.h.callService("number","set_value",{
          entity_id:command.entity_id,value:command.value});
        this.message("FTMS-målvärde skickat: "+command.value.toLocaleString("sv-SE")+
          (kind==="speed"?" km/h":" %")+". Kontrollera faktiskt värde på maskinen.");
      }catch(err){
        this.message("FTMS-kommandot misslyckades: "+(err?.message||err));
      }finally{
        this._stepBusy=false;
        if(this.chosen===key)this.draw();
      }
    }
    async setTarget(kind){
      const g=this.collect()[this.chosen],entry=g?.["target_"+kind],el=this.shadowRoot.querySelector('[data-target="'+kind+'"]');
      if(!entry||entry.state==="unavailable"||!el||el.value.trim()==="")return;
      if(this.deviceType(g)==="treadmill"&&!this.moving(g)){
        this.message("Starta löpbandet först innan du ändrar FTMS-målvärden.");
        return;
      }
      const v=Number(el.value);
      if(!Number.isFinite(v)||!el.checkValidity()){this.message("Otillåtet värde.");return;}
      // Exact target entry is behind the collapsed Advanced panel and shares
      // the same armed/moving limits; it does not prompt on every adjustment.
      await this.call("number","set_value",{entity_id:entry.id,value:v});
      el.value="";
    }
    async call(domain,service,data){
      try{await this.h.callService(domain,service,data);this.message("Kommando kvitterat av Home Assistant – kontrollera maskinens faktiska värde.");}
      catch(err){this.message("Kommandot misslyckades: "+(err?.message||err));}
    }
    message(v){const e=this.shadowRoot.querySelector(".message")||
      this.shadowRoot.querySelector("[data-fan-status]");if(e)e.textContent=v;}
  }
  if(!customElements.get("indoor-training-central-card"))customElements.define("indoor-training-central-card",Card);
  // Existing dashboards retain the legacy card type.
  if(!customElements.get("homefitnesscode-card"))customElements.define("homefitnesscode-card",class LegacyIndoorTrainingCard extends Card {});
  window.customCards=window.customCards||[];
  if(!window.customCards.some(card=>card.type==="indoor-training-central-card")){
    window.customCards.push({type:"indoor-training-central-card",name:"HA-IndoorTrainingCentral",description:"Inomhusträning: löpband, cykel, rodd och HEADWIND"});
  }
})();
