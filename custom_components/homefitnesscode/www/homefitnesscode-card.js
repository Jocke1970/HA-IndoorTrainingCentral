/* HomeFitnessCode: responsive Lovelace dashboard (no external JS dependencies). */
(() => {
  "use strict";
  const defs = {
    treadmill: {name:"Löpband", metrics:["speed_kmh","distance_km","elapsed_s","heart_rate_bpm","incline_percent","energy_kcal"],targets:["speed","incline"]},
    bike: {name:"Cykeltrainer",metrics:["power_w","cadence_rpm","speed_kmh","heart_rate_bpm","distance_km","elapsed_s","resistance_level"],targets:["power","resistance","incline"]},
    rower: {name:"Roddmaskin",metrics:["pace_s_per_500m","stroke_rate_spm","distance_km","stroke_count","elapsed_s","heart_rate_bpm","power_w"],targets:["resistance","power"]},
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
    set hass(h){this.h=h;this.draw();}
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
      ":host{display:block;color:var(--primary-text-color)}",
      "ha-card{border-radius:16px;overflow:hidden}",
      ".root{padding:20px;display:grid;gap:14px}",
      ".head{display:flex;justify-content:space-between;align-items:center;gap:16px}",
      ".kicker{font-weight:750;letter-spacing:.13em;font-size:11px;color:var(--secondary-text-color)}",
      "h2{margin:3px 0;font-size:23px}h3{margin:0 0 8px;font-size:16px}",
      ".sub,.foot{font-size:12px;color:var(--secondary-text-color)}",
      "select,input{font:inherit;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:9px;padding:9px;box-sizing:border-box;min-width:0}",
      ".stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px}",
      ".tile{padding:12px;border-radius:12px;background:var(--secondary-background-color)}",
      ".label{font-size:12px;color:var(--secondary-text-color)}",
      ".val{font-size:26px;font-weight:750;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}",
      ".unit{font-size:11px;color:var(--secondary-text-color)}",
      ".panel{border:1px solid var(--divider-color);padding:14px;border-radius:12px}",
      ".actions,.targetrow{display:flex;gap:8px;flex-wrap:wrap}",
      "button{font:inherit;font-size:13px;cursor:pointer;color:var(--primary-text-color);background:var(--secondary-background-color);border:1px solid var(--divider-color);border-radius:9px;padding:10px}",
      "button:disabled,input:disabled{opacity:.4;cursor:not-allowed}",
      ".danger{color:var(--error-color);border-color:var(--error-color)}",
      ".controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:15px}",
      ".target{display:grid;gap:6px;font-size:12px}",
      ".targetrow input{flex:1;width:80px}",
      ".note,.message{margin:8px 0;font-size:12px;color:var(--secondary-text-color)}",
      ".foot{display:flex;justify-content:space-between;gap:12px}",
      ".fan-line{display:flex;align-items:center;gap:12px;flex-wrap:wrap}",
      ".fan-percent{font-size:23px;font-weight:750}",
      ".fan-line select{max-width:210px}",
      ".fan-note{font-size:12px;color:var(--secondary-text-color);margin:4px 0}",
      "@media(max-width:680px){.root{padding:12px}.head{display:grid;gap:10px}select{width:100%}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.val{font-size:22px}.controls{grid-template-columns:1fr}.actions button{flex:1}}"
    ].join("");}
    shell(key,type,groups){
      const d=defs[type]||defs.auto;
      const opt=Object.keys(groups).sort().map(id=>'<option value="'+esc(id)+'"'+(id===key?' selected':'')+'>'+esc(groups[id]?.machine_type?.attributes?.hfc_device_name||id)+'</option>').join("");
      const tiles=d.metrics.map(m=>'<div class="tile"><div class="label">'+esc(label[m]||m)+'</div><div class="val" data-metric="'+m+'">–</div><div class="unit">'+esc(units[m]||"")+'</div></div>').join("");
      const targets=d.targets.map(m=>'<label class="target">'+esc(label[m])+'<span class="targetrow"><input type="number" inputmode="decimal" data-target="'+m+'"/><button type="button" data-set="'+m+'">Ställ in</button></span></label>').join("");
      const actions=['arm',...(type==='treadmill'?['start','pause','stop']:[])].map(a=>
        '<button type="button" data-action="'+a+'" '+(a==='stop'?'class="danger"':'')+'>'+({arm:"Aktivera styrning",start:"Start",pause:"Paus",stop:"Stopp"}[a])+'</button>').join("");
      const fanChoices=this.fans();
      const fanOptions=fanChoices.map(([id,s])=>'<option value="'+esc(id)+'"'+(this.fanSelected===id?' selected':'')+'>'+esc(s.attributes?.friendly_name||id)+'</option>').join("");
      const fanPanel=(type==="bike"||type==="headwind")?(
        '<section class="panel" data-fan><h3>💨 Wahoo HEADWIND</h3>'+
        (fanChoices.length?
          '<div class="fan-line"><select data-fan-choice aria-label="Välj fläkt">'+fanOptions+'</select><span class="fan-percent" data-fan-percent>–</span><span data-fan-status>Ej ansluten</span></div>'+
          '<div class="controls"><label class="target">Driftläge<select data-fan-mode><option value="off">Av</option><option value="manual">Manuell</option><option value="heart_rate">Puls (sensor i fläkten)</option><option value="speed">Hastighet (sensor i fläkten)</option></select></label>'+
          '<label class="target">Fläkthastighet (%)<span class="targetrow"><input data-fan-target type="number" min="0" max="100" step="5" inputmode="numeric" placeholder="0–100"/><button type="button" data-fan-apply>Ställ in</button></span></label></div>'+
          '<div class="actions"><button data-fan-preset="0" type="button">Av</button><button data-fan-preset="25" type="button">25 %</button><button data-fan-preset="50" type="button">50 %</button><button data-fan-preset="75" type="button">75 %</button><button data-fan-preset="100" type="button">100 %</button></div>'+
          '<p class="fan-note">Pulsstyrning via ditt parkopplade pulsband är huvudläge. HA ändrar inte fläktläget automatiskt. Effektstyrning/adaptiv kylning kräver nyare firmware och konfigureras i Wahoo-appen.</p><p class="fan-note" data-fan-fw>Firmware: okänd</p>'
          :'<p class="fan-note">Lägg till Wahoo HEADWIND som enhet i HomeFitnessCode för gemensam visning och styrning.</p>')+
        '</section>'
      ):"";
      const trainPanel=(type==="headwind"||type==="auto")?"":(
        '<section class="stats">'+tiles+'</section><section class="panel"><h3>Styrning</h3>'+
        '<p class="note">Manuell aktivering krävs. Ingen automatisk start efter återanslutning.</p>'+
        '<div class="actions">'+actions+'</div><div class="controls">'+targets+'</div>'+
        '<div class="message" aria-live="polite"></div></section>'
      );
      this.shadowRoot.innerHTML='<style>'+this.styleText()+'</style><ha-card><div class="root">'+
        '<header class="head"><div><div class="kicker">HOMEFITNESSCODE · FTMS</div><h2>'+d.name+'</h2><div class="sub" data-info>Ej ansluten</div></div>'+
        '<select aria-label="Välj träningsmaskin">'+opt+'</select></header>'+
        trainPanel+fanPanel+
        '<footer class="foot"><span data-protocol>Protokoll: –</span><span data-arm>Låst</span></footer>'+
        '</div></ha-card>';
      this.shadowRoot.querySelector('select').addEventListener('change',e=>{this.chosen=e.target.value;this.signature="";this.draw();});
      this.shadowRoot.querySelectorAll('[data-action]').forEach(b=>b.addEventListener('click',()=>this.action(b.dataset.action)));
      this.shadowRoot.querySelectorAll('[data-set]').forEach(b=>b.addEventListener('click',()=>this.setTarget(b.dataset.set)));
      this.shadowRoot.querySelector('[data-fan-choice]')?.addEventListener('change',e=>{this.fanSelected=e.target.value;this.signature="";this.draw();});
      this.shadowRoot.querySelector('[data-fan-mode]')?.addEventListener('change',e=>this.fanMode(e.target.value));
      this.shadowRoot.querySelector('[data-fan-apply]')?.addEventListener('click',()=>{
        const input=this.shadowRoot.querySelector('[data-fan-target]');
        if(input.value.trim()!==""&&input.checkValidity())this.fanPercent(Number(input.value));
      });
      this.shadowRoot.querySelectorAll('[data-fan-preset]').forEach(b=>b.addEventListener('click',()=>this.fanPercent(Number(b.dataset.fanPreset))));
      this.signature=key+':'+type+':'+Object.keys(groups).sort().join(',')+':'+this.fans().map(([id])=>id).join(',');
    }
    draw(){
      if(!this.h)return;
      if(!this.shadowRoot)this.attachShadow({mode:"open"});
      const groups=this.collect(),ids=Object.keys(groups).sort();
      if(!ids.length){this.shadowRoot.innerHTML='<ha-card><div style="padding:22px">Inga maskiner registrerade. Konfigurera HomeFitnessCode-integrationen först.</div></ha-card>';this.signature="";return;}
      const key=ids.includes(this.chosen)?this.chosen:ids[0];this.chosen=key;
      const g=groups[key];
      const rawType=this.value(g,"machine_type");
      const name=(g.connected?.attributes?.hfc_device_name||g.protocol?.attributes?.hfc_device_name||"").toUpperCase();
      const type=defs[rawType]?rawType:(g.headwind_fan?"headwind":
        name.includes("TACX")||name.includes("FLUX")?"bike":
        name.includes("WP5000")?"rower":"auto");
      if(this.signature!==key+':'+type+':'+ids.join(',')+':'+this.fans().map(([id])=>id).join(','))this.shell(key,type,groups);
      const connected=this.value(g,"connected")==="on",armed=this.value(g,"armed")==="on";
      this.shadowRoot.querySelector('[data-info]').textContent=(connected?"● Ansluten":"○ Frånkopplad")+
        (type==="headwind"?"":(" · "+(this.value(g,"session_status")||"väntar på anslutning")));
      this.shadowRoot.querySelector('[data-protocol]').textContent="Protokoll: "+(this.value(g,"protocol")||"–");
      this.shadowRoot.querySelector('[data-arm]').textContent=type==="headwind"?"Fläktstyrning separat":(armed?"Styrning aktiverad":"Styrning låst");
      this.shadowRoot.querySelectorAll('[data-metric]').forEach(el=>el.textContent=this.display(g,el.dataset.metric));
      this.shadowRoot.querySelectorAll('[data-action]').forEach(b=>{
        const e=g[b.dataset.action];
        b.disabled=!connected||!e||e.state==="unavailable";
      });
      this.refreshFan(type);
      this.shadowRoot.querySelectorAll('[data-target]').forEach(input=>{
        const e=g["target_"+input.dataset.target];
        input.disabled=!connected||!armed||!e||e.state==="unavailable";
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
      status.textContent=available?(fan.state==="on"?"På":"Av"):"Frånkopplad";
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
      if(name==="start"&&!confirm("Starta löpbandet? Säkerställ att området är fritt och säkerhetsnyckeln fungerar."))return;
      await this.call("button","press",{entity_id:entry.id});
    }
    async setTarget(kind){
      const g=this.collect()[this.chosen],entry=g?.["target_"+kind],el=this.shadowRoot.querySelector('[data-target="'+kind+'"]');
      if(!entry||entry.state==="unavailable"||!el||el.value.trim()==="")return;
      const v=Number(el.value);
      if(!Number.isFinite(v)||!el.checkValidity()){this.message("Otillåtet värde.");return;}
      if(kind==="speed"&&!confirm("Ändra hastigheten till "+v+" km/h?"))return;
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
  if(!customElements.get("homefitnesscode-card"))customElements.define("homefitnesscode-card",Card);
  window.customCards=window.customCards||[];
  window.customCards.push({type:"homefitnesscode-card",name:"HomeFitnessCode",description:"Responsive training dashboard for treadmill, bike and rower"});
})();
