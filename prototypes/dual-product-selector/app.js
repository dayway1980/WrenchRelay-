/* Demonstration only: fictional data, no network, no storage, no user input. */
const flows = {
 industrial: { name:"Industrial", steps:[
  {title:"Reported information", heading:"What the shift noticed", rows:[["Equipment","Example conveyor C-12 (fictional)"],["Symptom","Conveyor stopped following a restart"],["Measurements","None recorded"],["Fault code","Not verified"],["Prior action","Operator notified maintenance"]],note:"Fictional information is not evidence of a real machine condition."},
  {title:"Structured record", heading:"Draft maintenance handoff", rows:[["Summary","Conveyor stopped; cause undetermined"],["Evidence available","Reported operator observation"],["Evidence missing","Fault history, measurements and equipment-state confirmation"],["Record owner","Qualified maintenance reviewer"]],note:"CMMS-ready formatting is not a CMMS connection. Nothing is saved."},
  {title:"Human verification", heading:"Qualified reviewer checklist", rows:[["Confirm","Asset ID, symptom sequence and source"],["Safety","Follow approved site energy-control and machine-safety procedures"],["Investigate","Missing observations using approved diagnostic procedures"],["Approve","Human verifies the final record before official entry"]],note:"Never use this demo to authorize repair, bypass safeguarding or substitute for LOTO."}
 ] },
 automotive: { name:"Automotive", steps:[
  {title:"Reported information", heading:"What a fictional caller reported",rows:[["Vehicle","Example 2016 pickup (fictional)"],["Customer concern","Intermittent no-start"],["Drivability","Not determined"],["Callback","Needed; no phone number collected"],["Appointment","Not scheduled"]],note:"No calls are made, answered, recorded or routed."},
  {title:"Structured record", heading:"Draft advisor intake",rows:[["Customer concern","Intermittent no-start; unverified"],["Vehicle details","Year, make and model require confirmation"],["Callback","Must be gathered using an approved process"],["Scheduling","No appointment confirmed"],["Advisor action","Review and contact customer"]],note:"No actual customer record is created; this is a fictional sample."},
  {title:"Human verification", heading:"Advisor verification checklist",rows:[["Confirm","Callback and vehicle identifiers through approved intake"],["Ask","When the condition occurs and related warnings"],["Assess","Urgent safety or drivability concerns"],["Approve","Advisor confirms service and scheduling decisions"]],note:"No diagnosis, repair authorization, price or booking is promised."}
 ] }
};
const byId=id=>document.getElementById(id); let mode="industrial",step=0;
function addNode(tag,text,className){const e=document.createElement(tag);e.textContent=text;if(className)e.className=className;return e;}
function render(){
 const flow=flows[mode], item=flow.steps[step];
 byId("demo-heading").textContent="Fictional "+flow.name+" example";
 byId("demo-label").textContent=flow.name+" sample";
 byId("step-count").textContent=(step+1)+" OF 3";
 byId("step-status").textContent="Step "+(step+1)+" of 3";
 for(const key of Object.keys(flows)){const b=byId("mode-"+key);b.classList.toggle("selected",key===mode);b.setAttribute("aria-pressed",String(key===mode));}
 for(let i=0;i<3;i++){const node=byId("s"+(i+1));node.classList.toggle("active",i===step);node.classList.toggle("complete",i<step);node.querySelector("span").textContent=flow.steps[i].title;}
 const output=byId("content"); output.replaceChildren();
 output.appendChild(addNode("h3",item.heading));
 const dl=addNode("dl",undefined,"grid");
 for(const [label,value] of item.rows){const div=document.createElement("div");div.append(addNode("dt",label),addNode("dd",value));dl.appendChild(div);}
 output.append(dl,addNode("p",item.note,"caution"));
 byId("next").textContent=step===2?"Replay walkthrough ↺":"Next: "+flow.steps[step+1].title.toLowerCase()+" →";
}
for(const key of Object.keys(flows))byId("mode-"+key).addEventListener("click",()=>{mode=key;step=0;render();byId("demo-heading").scrollIntoView({behavior:"smooth",block:"start"});});
byId("next").addEventListener("click",()=>{step=(step+1)%3;render();});
byId("reset").addEventListener("click",()=>{step=0;render();});
render();
