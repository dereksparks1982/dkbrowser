"use strict";
// Run locally: node --test dk_browser/integrations/dk_live_block/chromium-dnr.test.cjs
const test=require("node:test");
const assert=require("node:assert/strict");
require("./runtime/rules.js"); // The original DK Live Block parser, unmodified.
const {compile,translate,MAX_DYNAMIC,create,compileTabPauses}=require("./chromium-dnr.js");
test("native and subscribed ABP rules become scoped DNR, no global widening",()=>{
 const text=[
  "||tracker.example^",
  "@@||cdn.example^$media,domain=videos.example",
  "||ads.example^$script,third-party,domain=site.example|~safe.site.example",
  "||anything.example^$removeparam=utm_*",
  "site.example##.advert"
 ].join("\n");
 const x=compile(text,{enabled:true,paused:["pause.example"]});
 assert.equal(x.rules.length,4);
 assert.equal(x.rules.filter(r=>r.action.type==="block").length,2);
 const allow=x.rules.find(r=>r.action.type==="allow");
 assert.deepEqual(allow.condition.initiatorDomains,["videos.example"]);
 assert.deepEqual(allow.condition.resourceTypes,["media"]);
 const third=x.rules.find(r=>r.condition.domainType==="thirdParty");
 assert.deepEqual(third.condition.excludedInitiatorDomains,["safe.site.example"]);
 const paused=x.rules.find(r=>r.action.type==="allowAllRequests");
 assert.deepEqual(paused.condition.requestDomains,["pause.example"]);
 assert.equal(compile(text,{enabled:false}).rules.length,0);
});
test("unrepresentable, invalid or broadening rules are discarded",()=>{
 const text=[
  "||ad.example^$script,unknown-option",
  "||ad.example^$removeparam=utm_*",
  "||ad.example^$redirect=noop.js,script",
  "||x.example^$script,domain=bad.*",
  "||safe.example^$script"
 ].join("\n");
 const x=compile(text,{enabled:true});
 assert.equal(x.rules.length,1);
 assert.equal(x.rules[0].condition.urlFilter,"||safe.example^");
});
test("badfilter prevents installing disabled original rules",()=>{
 const x=compile("||a.example^\n||a.example^$badfilter",{enabled:true});
 assert.equal(x.rules.length,0);
});
test("domain-allowlisted exceptions and limits never erase unrelated sites",()=>{
 const x=compile("||a.example^\n@@||b.example^$script,domain=site.example",
 {enabled:true,paused:["site.example","wrong-site/evil"]},100);
 assert.equal(x.rules.length,3);
 assert.ok(x.rules.every(r=>r.id>=1));
 assert.deepEqual(x.rules.find(r=>r.action.type==="allowAllRequests").condition.requestDomains,
 ["site.example"]);
 assert.ok(MAX_DYNAMIC>=5000);
});
test("atomic installed-rule refresh, disable and bad API failure handling",async()=>{
 let installed=[{id:88}],calls=[];
 const dnr={
  getDynamicRules:async()=>installed,
  updateDynamicRules:async args=>{
   calls.push(args);installed=args.addRules;
  }
 };
 const adapter=create(dnr);
 await adapter.sync("||ads.example^",{enabled:true});
 assert.equal(installed.length,1);
 assert.deepEqual(calls[0].removeRuleIds,[88]);
 await adapter.sync("||ads.example^",{enabled:false});
 assert.equal(installed.length,0);
 const unavailable=create(null);
 assert.match((await unavailable.sync("||ads.example^",{enabled:true})).error,/unavailable/);
});

test("turning protection off also disables the bundled static seed",async()=>{
 let dynamic=[],enabled=["dk_live_block_seed"];
 const api={
  getDynamicRules:async()=>dynamic,
  updateDynamicRules:async ({addRules})=>{dynamic=addRules;},
  getEnabledRulesets:async()=>[...enabled],
  updateEnabledRulesets:async ({enableRulesetIds=[],disableRulesetIds=[]})=>{
   enabled=enabled.filter(id=>!disableRulesetIds.includes(id));
   for(const id of enableRulesetIds)if(!enabled.includes(id))enabled.push(id);
  }
 };
 const adapter=create(api);
 assert.equal((await adapter.sync("||ads.example^",{enabled:false})).error,"");
 assert.deepEqual(dynamic,[]);
 assert.deepEqual(enabled,[]);
 assert.equal((await adapter.sync("||ads.example^",{enabled:true})).error,"");
 assert.equal(dynamic.length,1);
 assert.deepEqual(enabled,["dk_live_block_seed"]);
});
test("missing static ruleset API refuses a false successful disable",async()=>{
 const adapter=create({
  getDynamicRules:async()=>[],
  updateDynamicRules:async()=>{}
 });
 assert.match((await adapter.sync("||ads.example^",{enabled:false})).error,/toggle unavailable/);
});

test("manual blocks and remembered approvals become DNR site-scoped rules",()=>{
 const opts={enabled:true,paused:["news.example"],
  manualBlocks:[{site:"news.example",host:"cdn.example",type:"script"}],
  rememberedAllowances:[{site:"blog.example",host:"img.example",type:"image",scope:"remember"}]};
 const {rules}=compile("||ads.example^",opts);
 const manual=rules.find(r=>r.priority===30);
 assert.deepEqual(manual.condition.initiatorDomains,["news.example"]);
 assert.deepEqual(manual.condition.requestDomains,["cdn.example"]);
 assert.deepEqual(manual.condition.resourceTypes,["script"]);
 const allowed=rules.find(r=>r.priority===20);
 assert.deepEqual(allowed.condition.initiatorDomains,["blog.example"]);
 assert.equal(allowed.action.type,"allow");
 assert.equal(compile("||ads.example^",{...opts,enabled:false}).rules.length,0);
});
test("unsafe semantic widening is rejected for specialized request types",()=>{
 const x=compile("",{enabled:true,manualBlocks:[
  {site:"news.example",host:"cdn.example",type:"imageset"},
  {site:"news.example",host:"cdn.example",type:"beacon"},
  {site:"news.example",host:"cdn.example",type:"sub_frame"}
 ]});
 assert.equal(x.rules.length,1);
 assert.deepEqual(x.rules[0].condition.resourceTypes,["sub_frame"]);
 assert.equal(x.rejected,2);
});
test("manual rules survive quota pressure and cannot be displaced by subscriptions",()=>{
 const list=Array.from({length:20},(_,i)=>"||ads"+i+".example^").join("\n");
 const x=compile(list,{enabled:true,
  manualBlocks:[{site:"news.example",host:"cdn.example",type:"script"}],
  paused:["news.example"]},10);
 assert.equal(x.rules.length,10);
 assert.ok(x.rules.some(r=>r.priority===30));
 assert.ok(x.rules.some(r=>r.action.type==="allowAllRequests"));
 assert.equal(new Set(x.rules.map(r=>r.id)).size,x.rules.length);
});

test("per-tab DNR pause has higher priority and never becomes global",()=>{
 const list=compileTabPauses([12,13,12,-1,"12",14],true);
 assert.equal(list.length,3);
 assert.deepEqual(list.map(x=>x.condition.tabIds[0]),[12,13,14]);
 assert.ok(list.every(x=>x.action.type==="allowAllRequests"&&x.priority>30));
 assert.deepEqual(compileTabPauses([12],false),[]);
});
test("tab pauses are session-scoped and removed when no longer requested",async()=>{
 let sessions=[{id:99,priority:40}];
 const api={
  getSessionRules:async()=>sessions,
  updateSessionRules:async ({removeRuleIds,addRules})=>{
   assert.deepEqual(removeRuleIds,sessions.map(x=>x.id));
   sessions=addRules;
  }
 };
 const adapter=create(api);
 const on=await adapter.syncTabPauses([42],{enabled:true});
 assert.equal(on.error,"");
 assert.equal(on.paused,1);
 assert.deepEqual(sessions[0].condition.tabIds,[42]);
 const off=await adapter.syncTabPauses([42],{enabled:false});
 assert.equal(off.paused,0);
 assert.deepEqual(sessions,[]);
});
