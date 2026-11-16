"use strict";
// Run locally: node --test dk_browser/integrations/dk_live_block/chromium-dnr.test.cjs
const test=require("node:test");
const assert=require("node:assert/strict");
require("./runtime/rules.js"); // The original DK Live Block parser, unmodified.
const {compile,translate,MAX_DYNAMIC,create}=require("./chromium-dnr.js");
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
