"use strict";
// Source regression cases. Do not execute during source-only development.
// For later local validation: node --test dk_browser/integrations/dk_live_block/chromium-compat.test.cjs
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const source=fs.readFileSync(require.resolve("./chromium-compat.js"),"utf8");

function makeRuntime(){
 const listeners=new Set();
 const chrome={
  runtime:{
   getURL:path=>"chrome-extension://dk-browser-test/"+path,
   onMessage:{
    addListener:handler=>listeners.add(handler),
    removeListener:handler=>listeners.delete(handler),
    hasListener:handler=>listeners.has(handler)
   }
  },
  action:{}
 };
 const context={chrome,Promise};
 vm.runInNewContext(source,context,{filename:"chromium-compat.js"});
 function deliver(message){
  const responses=[],returns=[];
  for(const listener of [...listeners]){
   const result=listener(message,{id:"test"},value=>responses.push(value));
   returns.push(result);
  }
  return {responses,returns};
 }
 return {browser:context.browser,deliver,listeners};
}
test("synchronous undefined response does not steal another listener's reply",()=>{
 const r=makeRuntime();
 r.browser.runtime.onMessage.addListener(()=>undefined);
 r.browser.runtime.onMessage.addListener(()=>({ok:true}));
 const result=r.deliver({action:"status"});
 assert.equal(result.returns[0],false);
 assert.equal(result.returns[1],false);
 assert.equal(result.responses.length,1);
 assert.equal(result.responses[0].ok,true);
});
test("async response keeps the channel open and forwards rejection",async()=>{
 const r=makeRuntime();
 const first=()=>Promise.resolve({ok:true});
 r.browser.runtime.onMessage.addListener(first);
 let result=r.deliver({action:"success"});
 assert.deepEqual(result.returns,[true]);
 await Promise.resolve();
 assert.equal(result.responses[0].ok,true);
 r.browser.runtime.onMessage.removeListener(first);
 r.browser.runtime.onMessage.addListener(()=>Promise.reject(Error("denied")));
 result=r.deliver({action:"failure"});
 await Promise.resolve();
 await Promise.resolve();
 assert.match(result.responses[0].error,/denied/);
});
test("listener identity can be removed and queried using Firefox-style API",()=>{
 const r=makeRuntime(),fn=()=>({ok:1});
 r.browser.runtime.onMessage.addListener(fn);
 r.browser.runtime.onMessage.addListener(fn);
 assert.equal(r.listeners.size,1);
 assert.equal(r.browser.runtime.onMessage.hasListener(fn),true);
 r.browser.runtime.onMessage.removeListener(fn);
 assert.equal(r.listeners.size,0);
 assert.equal(r.browser.runtime.onMessage.hasListener(fn),false);
});
test("runtime getURL translates upstream paths but retains Chromium resources",()=>{
 const r=makeRuntime();
 assert.equal(r.browser.runtime.getURL("options.html"),
  "chrome-extension://dk-browser-test/runtime/options.html");
 assert.equal(r.browser.runtime.getURL("runtime/popup.html"),
  "chrome-extension://dk-browser-test/runtime/popup.html");
 assert.equal(r.browser.runtime.getURL("chromium-dnr.js"),
  "chrome-extension://dk-browser-test/chromium-dnr.js");
});
