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
 // Reserve room for user-selected controls before spending the full DNR
 // quota on subscription filters. They must not disappear on large lists.
 const reserved=Math.min(limit,(
   (Array.isArray(settings?.manualBlocks)?settings.manualBlocks.length:0)+
   (Array.isArray(settings?.rememberedAllowances)?settings.rememberedAllowances.length:0)+
   (Array.isArray(settings?.paused)?settings.paused.length:0)));
 rules.splice(Math.max(0,limit-reserved));
 const paused=(Array.isArray(settings?.paused)?settings.paused:[])
   .filter(validHost).slice(0,300);
 if(settings?.enabled!==false)for(const site of paused){
   if(rules.length>=limit)break;
   rules.push({id:rules.length+1,priority:10,
     action:{type:"allowAllRequests"},
     condition:{requestDomains:[site],resourceTypes:["main_frame","sub_frame"]}});
 }
 if(settings?.enabled!==false){
   const extras=extraRules(settings,rules.length+1,limit-rules.length);
   rules.push(...extras.rules);rejected+=extras.rejected;
 }
 return {rules:settings?.enabled===false?[]:rules,
   accepted:settings?.enabled===false?0:rules.length,rejected,
   limited:rules.length>=limit};
}
function create(api=root.chrome?.declarativeNetRequest){
 let queue=Promise.resolve(),stats={accepted:0,rejected:0,limited:false,error:"",updated:0};
 function sync(source,settings){
   const compiled=compile(source,settings);
   const operation=queue.catch(()=>{}).then(async()=>{
     if(!api?.getDynamicRules||!api?.updateDynamicRules) {
       stats={...compiled,error:"Chromium DNR API unavailable",updated:Date.now()};
       return stats;
     }
     try{
       const current=await api.getDynamicRules();
       await api.updateDynamicRules({
         removeRuleIds:current.map(item=>item.id),
         addRules:compiled.rules
       });
       // The bundled static seed is separate from dynamic rules. Disabling
       // protection must disable BOTH, or the switch still blocks requests.
       // Re-enable the seed only when protection is enabled again.
       if(api.getEnabledRulesets && api.updateEnabledRulesets){
         const seed="dk_live_block_seed";
         const enabled=await api.getEnabledRulesets();
         const hasSeed=enabled.includes(seed);
         const wantSeed=settings?.enabled!==false;
         if(hasSeed!==wantSeed){
           await api.updateEnabledRulesets(wantSeed?
             {enableRulesetIds:[seed]}:{disableRulesetIds:[seed]});
         }
       }else if(settings?.enabled===false){
         // A Chromium implementation without ruleset control cannot
         // truthfully report protection as fully disabled.
         throw new Error("Static ruleset toggle unavailable");
       }
       stats={accepted:compiled.accepted,rejected:compiled.rejected,
         limited:compiled.limited,error:"",updated:Date.now()};
     }catch(error){
       // Leave existing valid rules intact if Chromium rejects the refresh.
       stats={accepted:compiled.accepted,rejected:compiled.rejected,
         limited:compiled.limited,error:String(error?.message||error).slice(0,180),
         updated:Date.now()};
       console.warn("DK Live Block: Chromium network filters",stats.error);
     }
     return stats;
   });
   queue=operation;return operation;
 }
 return {sync,status:()=>({...stats})};
}
root.DKChromiumRules={compile,translate,create,MAX_DYNAMIC,domainList,explicitRule,extraRules};
if(typeof module!=="undefined")module.exports=root.DKChromiumRules;
})(typeof globalThis!=="undefined"?globalThis:this);
