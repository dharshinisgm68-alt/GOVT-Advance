const askForm=document.getElementById("askForm"),chat=document.getElementById("chat");
askForm.addEventListener("submit",async(e)=>{e.preventDefault();const input=document.getElementById("question"),q=input.value.trim();if(!q)return;
chat.innerHTML+=`<div class="message user"><b>You:</b> ${escapeHtml(q)}</div>`;input.value="";
const id="loading-"+Date.now();chat.innerHTML+=`<div class="message bot" id="${id}">⏳ Searching government scheme documents...</div>`;
try{const r=await fetch("/ask",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question:q})});const d=await r.json();document.getElementById(id)?.remove();
if(!r.ok||d.error){chat.innerHTML+=`<div class="message bot">❌ <b>Error:</b> ${escapeHtml(d.error||"Something went wrong")}</div>`;return;}
let sources="";if(d.sources?.length){sources=`<div class="source"><b>📚 Sources:</b><br>${d.sources.map(s=>`• ${escapeHtml(s.source)} - Page ${escapeHtml(String(s.page))}`).join("<br>")}</div>`;}
chat.innerHTML+=`<div class="message bot"><b>🤖 Assistant:</b><br><br>${escapeHtml(String(d.answer||"No answer received."))}${sources}</div>`;
}catch(err){document.getElementById(id)?.remove();chat.innerHTML+=`<div class="message bot">❌ <b>Connection error:</b> ${escapeHtml(err.message)}</div>`;}});
function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c]));}