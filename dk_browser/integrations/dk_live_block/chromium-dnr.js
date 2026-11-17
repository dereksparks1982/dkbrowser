/* DK Browser: Chromium DeclarativeNetRequest adapter for the original
 * DK Live Block Firefox filter engine. Existing DKRules.network() parser is
 * authoritative. Unrepresentable rules are skipped, NEVER broadened.
 *
 * Copyright (c) DK Softworks; original code: dkliveblock/LICENSE.
 */
(function(root){
"use strict";
const DNR_TYPES={
 "script":"script","image":"image","stylesheet":"stylesheet","media":"media",
 "font":"font","object":"object","xmlhttprequest":"xmlhttprequest",
 "subdocument":"sub_frame","document":"main_frame","ping":"ping",
 "websocket":"websocket","other":"other"
};
// DNR safe block/allow rules have a separate dynamic quota on recent Chromium.
 // Leave room for future site-allowlist and browser-owned rules.
const MAX_DYNAMIC=25000;
const validHost=h=>typeof h==="string"&&h.length<=253&&
 h.split(".").length>=2&&h.split(".").every(x=>
 /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(x));
function domainList(raw,excludedAllowed=true){
 if(!raw)return {include:[],exclude:[]};
 const include=[],exclude=[];
 for(const item of raw.split("|")){
   let h=item.trim().toLowerCase(),neg=h.startsWith("~");
   if(neg){if(!excludedAllowed)return null;h=h.slice(1);}
   if(!validHost(h))return null;
   (neg?exclude:include).push(h);
 }
 return include.length||exclude.length?{include,exclude}:null;
}
function translate(parsed,id){
 if(!parsed||parsed.badfilter||parsed.special||parsed.removeparam||
    parsed.redirect||!parsed.p||parsed.p.length>1000)return null;
 // Regex filter strings are not guaranteed to be valid Chromium RE2.
 // Raw ABP URL patterns map directly to DNR urlFilter syntax.
 if(parsed.p.startsWith("/")||parsed.p==="*"||/[^\x20-\x7e]/.test(parsed.p))
   return null;
 if(/[{}<>]/.test(parsed.p))return null;
 if(parsed.scope.includes(".*"))return null; // Entity syntax not in DNR.
 const init=domainList(parsed.scope);
 const target=domainList(parsed.targetScope,false);
 const deny=domainList(parsed.denyallow,false);
 if(!init||!target||!deny)return null;
 const condition={urlFilter:parsed.p};
 if(parsed.matchCase)condition.isUrlFilterCaseSensitive=true;
 const types=[],excluding=[];
 for(const item of parsed.include) {
   if(!DNR_TYPES[item])return null;
   types.push(DNR_TYPES[item]);
 }
 for(const item of parsed.exclude){
   if(!DNR_TYPES[item])return null;
   excluding.push(DNR_TYPES[item]);
 }
 if(types.length){
   condition.resourceTypes=Array.from(new Set(types));
   // A rule with both positive and negative types cannot be translated
   // without rewriting that semantics. Refuse instead of broadening.
   if(excluding.length)return null;
 }else if(excluding.length)condition.excludedResourceTypes=Array.from(new Set(excluding));
 // Always use extension-specific third-party semantics with no guessed
 // registrable domain. Chrome computes the request domain relationship.
 if(parsed.third!==null)condition.domainType=parsed.third?"thirdParty":"firstParty";
 if(init.include.length)condition.initiatorDomains=init.include;
 if(init.exclude.length)condition.excludedInitiatorDomains=init.exclude;
 if(target.include.length)condition.requestDomains=target.include;
 if(deny.include.length){
   if(!init.include.length)return null;
   condition.excludedRequestDomains=deny.include;
 }
 if(parsed.methods){
   const yes=[...parsed.methods.yes].map(x=>x.toLowerCase());
   const no=[...parsed.methods.no].map(x=>x.toLowerCase());
   if(yes.length&&no.length)return null;
   if(yes.length)condition.requestMethods=yes;
   if(no.length)condition.excludedRequestMethods=no;
 }
 return {id,priority:parsed.important?4:parsed.exception?3:1,
   action:{type:parsed.exception?"allow":"block"},condition};
}
// Chromium's DNR does not call the Firefox per-request decision handler.
// Compile explicit, exact site + destination + resource-type user choices as
// higher-priority rules. Unsupported request types are deliberately refused.
function explicitType(type){
 // Firefox distinguishes imageset and beacon from ordinary image/ping.
 // DNR cannot preserve those exact request kinds, so never broaden them.
 return Object.values(DNR_TYPES).includes(type)?type:null;
}
function explicitRule(row,id,allow){
 if(!row||!validHost(row.site)||!validHost(row.host))return null;
 const type=explicitType(row.type);
 if(!type||!["image","script","stylesheet","media","font","object",
    "xmlhttprequest","sub_frame","ping","websocket","other"].includes(type))return null;
 return {id,priority:allow?20:30,
  action:{type:allow?"allow":"block"},
  condition:{initiatorDomains:[row.site],requestDomains:[row.host],
   resourceTypes:[type]}};
}
function extraRules(settings,start,remaining){
 const result=[],duplicates=new Set();let rejected=0;
 function append(rows,allow){
  if(!Array.isArray(rows))return;
  for(const row of rows){
   if(result.length>=remaining)break;
   // Never turn temporary/session choices into browser-wide DNR rules:
   // DNR dynamic rules persist independently of the Firefox tab lifecycle.
   if(allow&&row.scope!=="remember")continue;
   const rule=explicitRule(row,start+result.length,allow);
   if(!rule){rejected++;continue;}
   const key=[allow?"allow":"block",row.site,row.host,row.type].join("|");
   if(duplicates.has(key))continue;
   duplicates.add(key);result.push(rule);
  }
 }
 // Respect explicit blocks first under quota pressure, then allowances.
 append(settings?.manualBlocks,false);
 append(settings?.rememberedAllowances,true);
 return {rules:result,rejected};
}
function compile(text,settings,max=MAX_DYNAMIC){
 if(typeof text!=="string")return {rules:[],rejected:0,accepted:0,limited:false};
 const lines=text.split(/\r?\n/),disabled=new Set(),pending=[],seen=new Set();
 let rejected=0;
 for(const raw of lines){
   const trimmed=raw.trim();
   if(!trimmed||trimmed.startsWith("!")||trimmed.startsWith("["))continue;
   const candidate=root.DKRules?.network?.(trimmed);
   if(!candidate){if(!root.DKRules?.cosmetic?.(trimmed)&&
       !root.DKRules?.procedural?.(trimmed))rejected++;continue;}
   if(candidate.badfilter){disabled.add(candidate.key);continue;}
   if(!seen.has(candidate.key)){seen.add(candidate.key);pending.push(candidate);}
 }
 const rules=[],limit=Math.min(MAX_DYNAMIC,Math.max(10,max));
 for(const entry of pending){
   if(disabled.has(entry.key))continue;
   const converted=translate(entry,rules.length+1);
   if(converted){rules.push(converted);if(rules.length>=limit)break;}
   else rejected++;
 }
 // Site-wide pauses must take precedence even over manual blocks (priority
 // 30), not just subscription rules. Grouping hostnames into two DNR rules
 // keeps hundreds of paused sites from consuming the dynamic rules quota.
 const paused=[...new Set((Array.isArray(settings?.paused)?settings.paused:[])
   .filter(validHost))].slice(0,300);
 const pauseSlots=paused.length?2:0;
 // Preserve enough slots for both pause rules and explicit user controls.
 const reserved=Math.min(limit,(
   (Array.isArray(settings?.manualBlocks)?settings.manualBlocks.length:0)+
   (Array.isArray(settings?.rememberedAllowances)?settings.rememberedAllowances.length:0)+
   pauseSlots));
 rules.splice(Math.max(0,limit-reserved));
 if(settings?.enabled!==false){
   // Manual blocks/remembered approvals retain their own exact destination
   // and request-type scopes even when subscription lists fill the quota.
   const extras=extraRules(settings,rules.length+1,
     Math.max(0,limit-rules.length-pauseSlots));
   rules.push(...extras.rules);rejected+=extras.rejected;
   if(paused.length&&rules.length+2<=limit){
     // Covers new document navigations and child frames, including their
     // subsequent requests. Higher priority defeats manual and DNR blocks.
     rules.push({id:rules.length+1,priority:50,
       action:{type:"allowAllRequests"},
       condition:{requestDomains:paused,resourceTypes:["main_frame","sub_frame"]}});
     // A site can be paused while its document is already loaded. This
     // initiator-scoped allow covers new subresource requests immediately,
     // without widening the exception to unrelated initiating websites.
     rules.push({id:rules.length+1,priority:50,action:{type:"allow"},
       condition:{initiatorDomains:paused,
         excludedResourceTypes:["main_frame"]}});
   }
 }
 return {rules:settings?.enabled===false?[]:rules,
   accepted:settings?.enabled===false?0:rules.length,rejected,
   limited:rules.length>=limit};
}
// Session-scoped Chromium rules, unlike dynamic rules, may use tabIds.
// A paused tab bypasses blocking in its own document/subframes only. Rule IDs
// are ephemeral and rebuilt from the current tab set after worker startup.
const MAX_PAUSED_TABS=250;
function compileTabPauses(tabIds,enabled=true){
 if(enabled===false||!Array.isArray(tabIds))return [];
 const ids=[...new Set(tabIds.filter(x=>Number.isSafeInteger(x)&&x>=0))].slice(0,MAX_PAUSED_TABS);
 return ids.map((tabId,index)=>({
  id:index+1,priority:40,action:{type:"allowAllRequests"},
  condition:{tabIds:[tabId],resourceTypes:["main_frame","sub_frame"]}
 }));
}
// Session rules can be scoped to a specific tab and can disappear at browser
// restart. Keep a conservative bounded subset below Chrome's session quota.
const MAX_SESSION_RULES=2500;
function compileSessionAllowances(settings,now=Date.now()){
 const rules=[],seen=new Set();let rejected=0;
 function append(rows,scope){
  if(!Array.isArray(rows))return;
  for(const row of rows){
   if(rules.length>=MAX_SESSION_RULES-MAX_PAUSED_TABS)break;
   if(row?.scope!==scope){rejected++;continue;}
   if(scope==="temporary"&&(!Number.isSafeInteger(row.tabId)||
      row.tabId<0||!Number.isSafeInteger(row.expires)||row.expires<=now)){
    rejected++;continue;
   }
   const rule=explicitRule(row,1000+rules.length,true);
   if(!rule){rejected++;continue;}
   const key=[scope,row.site,row.host,row.type,
    scope==="temporary"?row.tabId:""].join("|");
   if(seen.has(key))continue;
   seen.add(key);
   // Explicit manual blocks (priority 30) still take precedence.
   rule.priority=25;
   if(scope==="temporary")rule.condition.tabIds=[row.tabId];
   rules.push(rule);
  }
 }
 append(settings?.sessionAllowances,"session");
 append(settings?.temporaryAllowances,"temporary");
 return {rules,rejected};
}
function compileSessionRules(tabIds,settings,now=Date.now()){
 const pauses=compileTabPauses(tabIds,settings?.enabled!==false);
 if(settings?.enabled===false)
  return {rules:[],paused:0,allowances:0,rejected:0};
 const extras=compileSessionAllowances(settings,now);
 const allowances=extras.rules.slice(0,MAX_SESSION_RULES-pauses.length);
 return {rules:[...pauses,...allowances],paused:pauses.length,
  allowances:allowances.length,rejected:extras.rejected+
   extras.rules.length-allowances.length};
}
function create(api=root.chrome?.declarativeNetRequest){
 let queue=Promise.resolve(),stats={accepted:0,rejected:0,limited:false,error:"",updated:0};
 let tabsStatus={paused:0,allowances:0,rejected:0,error:"",updated:0};
 const seed="dk_live_block_seed";
 function sync(source,settings){
  const compiled=compile(source,settings);
  const operation=queue.catch(()=>{}).then(async()=>{
   if(!api?.getDynamicRules||!api?.updateDynamicRules){
    stats={...stats,error:"Chromium DNR API unavailable",updated:Date.now()};
    return {...stats};
   }
   const wantSeed=settings?.enabled!==false;
   // Never remove dynamic rules when the caller expects protection to turn
   // fully off but Chromium cannot control our always-on static seed.
   if(!api.getEnabledRulesets||!api.updateEnabledRulesets){
    stats={...stats,error:"Static ruleset toggle unavailable",updated:Date.now()};
    return {...stats};
   }
   let previous=[],previousCount=stats.accepted,hadSeed=null;
   let changedDynamic=false,changedSeed=false,rollbackError="";
   try{
    previous=await api.getDynamicRules();
    previousCount=previous.length;
    if(api.getEnabledRulesets&&api.updateEnabledRulesets){
     hadSeed=(await api.getEnabledRulesets()).includes(seed);
    }
    // When turning protection OFF, disable the static seed first. When
    // turning it ON, add the dynamic filters first. On either path a later
    // failure restores the previous state, rather than silently reporting
    // that both backends are synchronized.
    if(!wantSeed&&hadSeed===true){
     await api.updateEnabledRulesets({disableRulesetIds:[seed]});
     changedSeed=true;
    }
    await api.updateDynamicRules({
     removeRuleIds:previous.map(rule=>rule.id),
     addRules:compiled.rules
    });
    changedDynamic=true;
    if(wantSeed&&hadSeed===false){
     await api.updateEnabledRulesets({enableRulesetIds:[seed]});
     changedSeed=true;
    }
    stats={accepted:compiled.accepted,rejected:compiled.rejected,
     limited:compiled.limited,error:"",updated:Date.now()};
   }catch(error){
    // DNR updateDynamicRules is atomic within the dynamic ruleset, but
    // toggling a static ruleset is a separate API operation. Roll back both
    // sides when necessary. Never claim the intended state after failure.
    if(changedDynamic){
     try{
      const current=await api.getDynamicRules();
      await api.updateDynamicRules({
       removeRuleIds:current.map(rule=>rule.id),addRules:previous
      });
     }catch(rollback){rollbackError="; dynamic rollback failed: "+
      String(rollback?.message||rollback).slice(0,100);}
    }
    if(changedSeed){
     try{
      await api.updateEnabledRulesets(hadSeed?
       {enableRulesetIds:[seed]}:{disableRulesetIds:[seed]});
     }catch(rollback){rollbackError+="; static rollback failed: "+
      String(rollback?.message||rollback).slice(0,100);}
    }
    stats={...stats,accepted:previousCount,
     error:(String(error?.message||error)+rollbackError).slice(0,250),
     updated:Date.now()};
    console.warn("DK Live Block: Chromium network filters",stats.error);
   }
   return {...stats};
  });
  queue=operation;return operation;
 }
 function syncTabPauses(tabIds,settings){
  const compiled=compileSessionRules(tabIds,settings);
  const operation=queue.catch(()=>{}).then(async()=>{
   if(!api?.getSessionRules||!api?.updateSessionRules){
    tabsStatus={...tabsStatus,
     error:"Chromium DNR session rules unavailable",updated:Date.now()};
    return {...tabsStatus};
   }
   let previousPaused=tabsStatus.paused;
   let previousAllowances=tabsStatus.allowances;
   try{
    const current=await api.getSessionRules();
    previousPaused=current.filter(rule=>rule.action?.type==="allowAllRequests").length;
    previousAllowances=current.filter(rule=>rule.action?.type==="allow").length;
    await api.updateSessionRules({
     removeRuleIds:current.map(rule=>rule.id),addRules:compiled.rules
    });
    tabsStatus={paused:compiled.paused,allowances:compiled.allowances,
     rejected:compiled.rejected,error:"",updated:Date.now()};
   }catch(error){
    // A rejected batch does not erase the previously installed rules.
    tabsStatus={...tabsStatus,paused:previousPaused,
     allowances:previousAllowances,
     error:String(error?.message||error).slice(0,180),updated:Date.now()};
   }
   return {...tabsStatus};
  });
  queue=operation;return operation;
 }
 return {sync,syncTabPauses,status:()=>({...stats,tabPauses:{...tabsStatus}})};
}
root.DKChromiumRules={compile,translate,create,MAX_DYNAMIC,MAX_SESSION_RULES,
 domainList,explicitRule,extraRules,compileTabPauses,compileSessionAllowances,
 compileSessionRules};
if(typeof module!=="undefined")module.exports=root.DKChromiumRules;
})(typeof globalThis!=="undefined"?globalThis:this);
