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
 runtime.onMessage={
  addListener(handler){
   // Firefox allows returning Promise<response> from onMessage. Chromium's
   // callback bridge keeps the extension response channel alive until done.
   listeners.addListener((msg,sender,reply)=>{
     let result;
     try{result=handler(msg,sender);}
     catch(error){reply({error:String(error?.message||error).slice(0,120)});return false;}
     Promise.resolve(result).then(value=>reply(value===undefined?{}:value),
       error=>reply({error:String(error?.message||error).slice(0,120)}));
     return true;
   });
  }
 };
}
api.runtime=runtime;
api.browserAction=ext.action;
root.browser=api;
root.DKChromiumRuntime=Object.freeze({dnr:!!ext.declarativeNetRequest,
 source:"DK Live Block bundled in DK Browser",manifestVersion:3});
})(typeof globalThis!=="undefined"?globalThis:this);
