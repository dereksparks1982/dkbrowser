/* DK Browser / DK Live Block: minimal Chromium MV3 compatibility.
 * This shim preserves the Firefox project's global "browser" API contract
 * without inventing unsupported privileged APIs or bypassing permissions.
 */
(function(root){
"use strict";
if(typeof root.chrome==="undefined")return;
const ext=root.chrome;
const api=Object.create(ext);
const runtime=Object.create(ext.runtime);
const getURL=ext.runtime.getURL.bind(ext.runtime);
runtime.getURL=(path="")=>{
 const value=String(path||"");
 if(!value)return getURL("");
 if(value.startsWith("runtime/")||value.startsWith("chromium-")||
    value==="rules.json")return getURL(value);
 return getURL("runtime/"+value.replace(/^\/+/,""));
};
if(ext.runtime.onMessage){
 const listeners=ext.runtime.onMessage;
 const bridges=new WeakMap();
 const failure=error=>({error:String(error?.message||error).slice(0,120)});
 runtime.onMessage={
  addListener(handler){
   if(typeof handler!=="function"||bridges.has(handler))return;
   // Firefox treats an undefined listener result as "not handled".
   // Replying with {} here can steal another listener's real response.
   const bridged=(msg,sender,reply)=>{
     let result;
     try{result=handler(msg,sender);}
     catch(error){reply(failure(error));return false;}
     if(result===undefined)return false;
     if(!result||typeof result.then!=="function"){
       reply(result);return false;
     }
     Promise.resolve(result).then(value=>reply(value===undefined?{}:value),
       error=>reply(failure(error)));
     return true; // Keep the channel alive for an actual async response.
   };
   bridges.set(handler,bridged);
   listeners.addListener(bridged);
  },
  removeListener(handler){
   const bridged=bridges.get(handler);
   if(bridged){listeners.removeListener(bridged);bridges.delete(handler);}
  },
  hasListener(handler){
   const bridged=bridges.get(handler);
   return !!bridged&&listeners.hasListener(bridged);
  }
 };
}
api.runtime=runtime;
api.browserAction=ext.action;
root.browser=api;
root.DKChromiumRuntime=Object.freeze({dnr:!!ext.declarativeNetRequest,
 source:"DK Live Block bundled in DK Browser",manifestVersion:3});
})(typeof globalThis!=="undefined"?globalThis:this);
