/* ====================================================================
   Baby Shower · Lista de Regalos — lógica del cliente
   ==================================================================== */
const $  = (s, el=document) => el.querySelector(s);
const $$ = (s, el=document) => [...el.querySelectorAll(s)];

const state = {
  gifts: [],
  filter: "all",
  hostKey: localStorage.getItem("bs_host_key") || "",   // clave de anfitriona (si la activó)
  myName: localStorage.getItem("bs_name") || "",        // recuerda el nombre del invitado
};

/* -------------------- utilidades -------------------- */
function toast(msg, type="ok"){
  const t = $("#toast");
  t.textContent = msg;
  t.className = "toast show " + type;
  t.hidden = false;
  clearTimeout(toast._t);
  toast._t = setTimeout(()=>{ t.classList.remove("show"); }, 2600);
}
async function api(url, opts){
  const r = await fetch(url, { headers:{"Content-Type":"application/json"}, ...opts });
  const data = await r.json().catch(()=>({}));
  return { ok:r.ok, status:r.status, data };
}
function esc(s){ return (s||"").replace(/[&<>"']/g, c => (
  {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#x27;"}[c])); }

/* -------------------- cargar y pintar -------------------- */
async function load(){
  const { ok, data } = await api("/api/gifts");
  if(!ok){ toast("No se pudo cargar la lista", "err"); return; }
  state.gifts = data.gifts;
  render();
  updateProgress(data.taken, data.total);
}

function updateProgress(taken, total){
  const pct = total ? Math.round(taken/total*100) : 0;
  $("#progress-bar").style.width = pct + "%";
  $("#progress-pct").textContent = pct + "%";
  $("#progress-text").textContent = `${taken} de ${total} regalos apartados`;
}

function visible(){
  if(state.filter==="free")  return state.gifts.filter(g=>!g.reserved);
  if(state.filter==="taken") return state.gifts.filter(g=> g.reserved);
  return state.gifts;
}

function render(){
  const grid = $("#grid");
  const list = visible();
  $("#empty").hidden = list.length>0;
  grid.innerHTML = list.map(cardHTML).join("");
}

function cardHTML(g){
  const thumb = g.image_url
    ? `<div class="photo"><img src="${esc(g.image_url)}" alt="" loading="lazy"></div>`
    : `<div class="thumb">${esc(g.emoji||"🎁")}</div>`;
  const del = `<button class="del" title="Eliminar" onclick="onDelete(${g.id})">✕</button>`;
  const myl = (state.myName||"").toLowerCase();
  const reservers = g.reservers || [];
  const mine = reservers.some(n => n.toLowerCase() === myl);
  const pill = g.qty > 1
    ? `<span class="qty-pill ${g.reserved?'full':''}">${g.count} de ${g.qty} apartados</span>` : "";
  const who = g.count > 0
    ? `<p class="reservers">${g.qty>1?'Lo llevan':'Lo lleva'}: <b>${reservers.map(esc).join(", ")}</b></p>` : "";

  // Caso 1: yo ya lo aparté
  if(mine){
    return `<article class="card taken" data-id="${g.id}">
      ${del}<span class="ribbon">Tu regalo</span>${thumb}
      <h3>${esc(g.name)}</h3>${pill}${who}
      <button class="btn btn-release" onclick="onRelease(${g.id},'${esc(g.name)}')">Liberar el mío</button>
    </article>`;
  }
  // Caso 2: completo (lo llevan otros)
  if(g.reserved){
    return `<article class="card taken" data-id="${g.id}">
      ${del}<span class="ribbon">${g.qty>1?'Completo':'Apartado'}</span>${thumb}
      <h3>${esc(g.name)}</h3>${pill}${who}
    </article>`;
  }
  // Caso 3: disponible
  return `<article class="card" data-id="${g.id}">
    ${del}${thumb}<h3>${esc(g.name)}</h3>${pill}${who}
    <button class="btn btn-reserve" onclick="onReserve(${g.id},'${esc(g.name)}','${esc(g.emoji||"🎁")}')">Apartar este</button>
  </article>`;
}

/* -------------------- modal genérico -------------------- */
function openSheet(html){
  $("#sheet").innerHTML = `<div class="grab"></div>` + html;
  $("#overlay").hidden = false;
}
function closeSheet(){ $("#overlay").hidden = true; }
$("#overlay").addEventListener("click", e=>{ if(e.target.id==="overlay") closeSheet(); });

/* -------------------- apartar -------------------- */
function onReserve(id, name, emoji){
  openSheet(`
    <h2>Apartar regalo</h2>
    <div class="gift-line"><span class="e">${emoji}</span><strong>${name}</strong></div>
    <div class="field">
      <label>Tu nombre</label>
      <input id="resName" type="text" placeholder="Ej. Tía Carmen" value="${esc(state.myName)}" maxlength="40" autocomplete="name">
    </div>
    <div class="actions">
      <button class="btn-ghost" onclick="closeSheet()">Cancelar</button>
      <button class="btn-primary" id="resGo">Confirmar 💙</button>
    </div>
    <p class="hint">Quedará reservado a tu nombre para que nadie más lo lleve.</p>
  `);
  const input = $("#resName"); input.focus();
  $("#resGo").onclick = async ()=>{
    const nm = input.value.trim();
    if(!nm){ input.focus(); toast("Escribe tu nombre 🙂","err"); return; }
    $("#resGo").disabled = true; $("#resGo").textContent = "Apartando…";
    const { ok, status, data } = await api("/api/reserve", {method:"POST", body:JSON.stringify({id, name:nm})});
    if(ok && data.ok){
      state.myName = nm; localStorage.setItem("bs_name", nm);
      closeSheet(); toast("¡Listo! Regalo apartado 🎁","ok"); load();
    } else {
      toast(data.error || "No se pudo apartar","err");
      if(status===409){ closeSheet(); load(); }
      else { $("#resGo").disabled=false; $("#resGo").textContent="Confirmar 💙"; }
    }
  };
}

/* -------------------- liberar -------------------- */
function onRelease(id, giftName){
  openSheet(`
    <h2>Liberar regalo</h2>
    <div class="gift-line"><span class="e">↩︎</span><strong>${giftName}</strong></div>
    <div class="field">
      <label>Confirma tu nombre</label>
      <input id="relName" type="text" placeholder="El nombre con que lo apartaste" value="${esc(state.myName)}" maxlength="40">
    </div>
    <div class="actions">
      <button class="btn-ghost" onclick="closeSheet()">Cancelar</button>
      <button class="btn-gold" id="relGo">Liberar</button>
    </div>
    <p class="hint">Volverá a estar disponible para los demás invitados.</p>
  `);
  $("#relName").focus();
  $("#relGo").onclick = async ()=>{
    const nm = $("#relName").value.trim();
    const { ok, data } = await api("/api/release", {method:"POST",
      body:JSON.stringify({id, name:nm, host_key:state.hostKey})});
    if(ok && data.ok){ closeSheet(); toast("Regalo liberado","ok"); load(); }
    else toast(data.error || "No se pudo liberar","err");
  };
}

/* -------------------- RSVP: confirmar asistencia -------------------- */
async function loadRsvp(){
  const url = state.hostKey ? `/api/rsvp?host_key=${encodeURIComponent(state.hostKey)}` : "/api/rsvp";
  const { ok, data } = await api(url);
  if(!ok) return;
  state.rsvp = data;
  const el = $("#rsvpCount");
  if(data.people === 0){
    el.textContent = "Sé el primero en confirmar 💙";
  } else {
    el.textContent = `${data.total} persona${data.total!==1?"s":""} confirmada${data.total!==1?"s":""}`
      + (data.names.length ? ` · ${data.names.slice(0,3).join(", ")}${data.names.length>3?"…":""}` : "");
  }
}

$("#rsvpBtn").onclick = ()=>{
  openSheet(`
    <h2>Confirmar asistencia</h2>
    <p class="hint" style="margin:0 0 16px">Nos encantará tenerte. Cuéntanos quién viene 💙</p>
    <div class="field"><label>Tu nombre</label>
      <input id="rvName" type="text" placeholder="Ej. Familia Pérez" value="${esc(state.myName)}" maxlength="40" autocomplete="name"></div>
    <div class="field"><label>¿Cuántos acompañantes? (sin contarte)</label>
      <input id="rvGuests" type="number" min="0" max="20" inputmode="numeric" value="0"></div>
    <div class="field"><label>Mensaje para los papás (opcional)</label>
      <input id="rvMsg" type="text" placeholder="Ej. ¡Felicidades, ahí estaremos!" maxlength="200"></div>
    <div class="actions">
      <button class="btn-ghost" onclick="closeSheet()">Cancelar</button>
      <button class="btn-gold" id="rvGo">Confirmar 💌</button>
    </div>
  `);
  $("#rvName").focus();
  $("#rvGo").onclick = async ()=>{
    const name = $("#rvName").value.trim();
    if(!name){ $("#rvName").focus(); toast("Escribe tu nombre 🙂","err"); return; }
    $("#rvGo").disabled = true; $("#rvGo").textContent = "Enviando…";
    const body = { name, guests:$("#rvGuests").value, message:$("#rvMsg").value.trim() };
    const { ok, data } = await api("/api/rsvp", {method:"POST", body:JSON.stringify(body)});
    if(ok && data.ok){
      state.myName = name; localStorage.setItem("bs_name", name);
      closeSheet(); toast("¡Gracias por confirmar! 💙","ok"); loadRsvp();
    } else {
      toast((data && data.error) || "No se pudo confirmar","err");
      $("#rvGo").disabled=false; $("#rvGo").textContent="Confirmar 💌";
    }
  };
};

$("#rsvpListBtn").onclick = async ()=>{
  await loadRsvp();
  const items = (state.rsvp && state.rsvp.items) || [];
  const rows = items.length ? items.map(g=>`
    <div class="guest-row">
      <div class="av">${esc((g.name||"?").trim().charAt(0).toUpperCase())}</div>
      <div style="flex:1">
        <div class="gn">${esc(g.name)}</div>
        ${g.message?`<div class="gm">“${esc(g.message)}”</div>`:""}
      </div>
      <div class="gg">${1+(g.guests||0)} ${1+(g.guests||0)===1?"persona":"personas"}</div>
    </div>`).join("") : `<p class="hint" style="padding:20px 0">Aún no hay confirmaciones.</p>`;
  openSheet(`
    <h2>Confirmados</h2>
    <p class="hint" style="margin:6px 0 4px">${state.rsvp.people} respuesta(s) · ${state.rsvp.total} persona(s) en total</p>
    <div class="guest-list">${rows}</div>
    <div class="actions"><button class="btn-primary" onclick="closeSheet()">Cerrar</button></div>
  `);
};

/* -------------------- filtros -------------------- */
$$(".chip").forEach(c=> c.onclick = ()=>{
  $$(".chip").forEach(x=>x.classList.remove("active"));
  c.classList.add("active");
  state.filter = c.dataset.filter;
  render();
});

/* -------------------- modo anfitriona -------------------- */
function applyHostUI(){
  document.body.classList.toggle("host", !!state.hostKey);
  const btn = $("#hostToggle");
  btn.textContent = state.hostKey ? "✓ Modo anfitriona (agregar/eliminar) · salir" : "⚙︎ Soy la anfitriona";
  if(typeof loadRsvp === "function") loadRsvp();  // recarga detalles de confirmados
}
$("#hostToggle").onclick = ()=>{
  if(state.hostKey){
    state.hostKey=""; localStorage.removeItem("bs_host_key"); applyHostUI();
    toast("Modo anfitriona desactivado"); return;
  }
  openSheet(`
    <h2>Modo anfitriona</h2>
    <p class="hint" style="margin:0 0 16px">Ingresa tu clave para poder agregar o eliminar regalos.</p>
    <div class="field"><label>Clave</label><input id="hk" type="password" placeholder="••••••" autocomplete="off"></div>
    <div class="actions">
      <button class="btn-ghost" onclick="closeSheet()">Cancelar</button>
      <button class="btn-primary" id="hkGo">Entrar</button>
    </div>
  `);
  $("#hk").focus();
  $("#hkGo").onclick = async ()=>{
    const key = $("#hk").value.trim();
    if(!key){ return; }
    // valida la clave intentando una operación inofensiva (agregar se valida en backend);
    // aquí solo la guardamos y mostramos los controles. El backend rechaza si es incorrecta.
    state.hostKey = key; localStorage.setItem("bs_host_key", key);
    applyHostUI(); closeSheet();
    openAddGift(); // muestra de una vez el formulario para agregar
  };
};

function openAddGift(){
  openSheet(`
    <h2>Agregar regalo</h2>
    <div class="field"><label>Nombre del regalo</label><input id="gName" placeholder="Ej. Termómetro digital" maxlength="80"></div>
    <div class="field"><label>Nota (opcional)</label><input id="gNote" placeholder="Ej. Color celeste" maxlength="120"></div>
    <div class="field"><label>Emoji (opcional)</label><input id="gEmoji" placeholder="🍼" maxlength="8"></div>
    <div class="field"><label>Cantidad (cuántos se pueden regalar)</label><input id="gQty" type="number" min="1" max="20" value="1"></div>
    <div class="actions">
      <button class="btn-ghost" onclick="closeSheet()">Cerrar</button>
      <button class="btn-gold" id="gGo">Agregar 🎁</button>
    </div>
    <p class="hint">Tip: deja esta lista lista antes de compartir el link con tus invitados.</p>
  `);
  $("#gName").focus();
  $("#gGo").onclick = async ()=>{
    const name = $("#gName").value.trim();
    if(!name){ $("#gName").focus(); return; }
    const body = { host_key:state.hostKey, name, note:$("#gNote").value.trim(), emoji:$("#gEmoji").value.trim(), qty:$("#gQty").value };
    const { ok, status, data } = await api("/api/gifts", {method:"POST", body:JSON.stringify(body)});
    if(ok && data.ok){ toast("Regalo agregado 🎁","ok"); openAddGift(); load(); }
    else if(status===403){ toast("Clave incorrecta","err"); state.hostKey=""; localStorage.removeItem("bs_host_key"); applyHostUI(); closeSheet(); }
    else toast(data.error || "No se pudo agregar","err");
  };
}

async function onDelete(id){
  if(!state.hostKey) return;
  if(!confirm("¿Eliminar este regalo de la lista?")) return;
  const { ok, status, data } = await api(`/api/gifts/${id}`, {method:"DELETE", body:JSON.stringify({host_key:state.hostKey})});
  if(ok && data.ok){ toast("Regalo eliminado"); load(); }
  else if(status===403){ toast("Clave incorrecta","err"); }
  else toast("No se pudo eliminar","err");
}

/* doble función del botón anfitriona: si ya está activa, un toque largo abre "agregar" */
$("#hostToggle").addEventListener("dblclick", ()=>{ if(state.hostKey) openAddGift(); });

/* -------------------- init -------------------- */
function refresh(){ load(); loadRsvp(); }
applyHostUI();
refresh();
setInterval(refresh, 15000); // refresca cada 15s para ver reservas y confirmaciones
document.addEventListener("visibilitychange", ()=>{ if(!document.hidden) refresh(); });
