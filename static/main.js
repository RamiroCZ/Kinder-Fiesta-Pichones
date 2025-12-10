// Exponer funciones globales si usas onclick en HTML
window.toggleAdmin = toggleAdmin;
window.openModal = openModal;
window.closeModal = closeModal;
window.eliminarComentario = eliminarComentario; // necesario por el onclick en comentarios



// ===== Utilidad =====
function esc(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

// ===== DOM listo =====
document.addEventListener("DOMContentLoaded", () => {
  // Botones header
  const adminBtn = document.getElementById("adminBtn");
  const sugerirBtn = document.getElementById("sugerirBtn");
  if (adminBtn) adminBtn.addEventListener("click", toggleAdmin);
  if (sugerirBtn) sugerirBtn.addEventListener("click", () => openModal("modalSugerir"));

  // Cerrar modales con la X
  document.querySelectorAll(".close[data-close]").forEach(x => {
    x.addEventListener("click", () => closeModal(x.getAttribute("data-close")));
  });

  // Formularios modales
  const loginForm = document.getElementById("adminLoginForm");
  if (loginForm) loginForm.addEventListener("submit", loginAdmin);

  const sugerirForm = document.getElementById("sugerirForm");
  if (sugerirForm) sugerirForm.addEventListener("submit", sugerirSalon);

  // Estado admin
  actualizarBotonAdmin();
  if (sessionStorage.getItem("admin") === "true") {
    mostrarBotonesAdmin();
  } else {
    ocultarBotonesAdmin();
  }

  // Búsqueda
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", function () {
      const query = this.value.toLowerCase();
      document.querySelectorAll(".salon").forEach(salon => {
        const nombre = salon.dataset.nombre || "";
        salon.style.display = nombre.includes(query) ? "" : "none";
      });
    });
  }

  // Carruseles
  document.querySelectorAll(".imagen-rotativa").forEach(container => {
    const imgEl = container.querySelector("img");
    let imgs;
    try { imgs = JSON.parse(imgEl.dataset.imgs || "[]"); } catch { imgs = []; }
    if (!Array.isArray(imgs) || imgs.length === 0) imgs = [imgEl.getAttribute("src")];

    startTimer(container, imgEl, imgs, 4000);

    container.querySelector(".flecha.izq")?.addEventListener("click", () => {
      const cur = parseInt(imgEl.dataset.index || "0", 10);
      setImage(imgEl, imgs, (cur - 1 + imgs.length) % imgs.length);
      startTimer(container, imgEl, imgs, 4000);
    });

    container.querySelector(".flecha.der")?.addEventListener("click", () => {
      const cur = parseInt(imgEl.dataset.index || "0", 10);
      setImage(imgEl, imgs, (cur + 1) % imgs.length);
      startTimer(container, imgEl, imgs, 4000);
    });
  });

  // Cargar comentarios al abrir
  document.querySelectorAll("details").forEach(d => {
    d.addEventListener("toggle", () => {
      if (!d.open) return;
      const section = d.closest(".salon");
      if (!section) return;
      const salonId = parseInt(section.id.split("-")[1], 10);
      cargarComentarios(salonId);
    });
  });
  

  // Enviar comentarios
  document.querySelectorAll(".comentario-form").forEach(form => {
    form.addEventListener("submit", ev => {
      ev.preventDefault();
      const salonId = parseInt(form.dataset.salonId, 10);
      enviarComentario(ev, salonId);
    });
  });
});

// ===== Modales =====
function openModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "grid";
}
function closeModal(id) {
  const el = document.getElementById(id);
  if (el) el.style.display = "none";
}

// ===== Carrusel helpers =====
function setImage(imgEl, imgs, index) {
  imgEl.dataset.index = String(index);
  imgEl.style.opacity = 0;
  setTimeout(() => {
    const src = imgs[index];
    imgEl.src = src.startsWith("/static/") ? src : "/static/" + src;
    imgEl.style.opacity = 1;
  }, 160);
}
function startTimer(container, imgEl, imgs, intervalMs = 4000) {
  stopTimer(container);
  const id = setInterval(() => {
    const cur = parseInt(imgEl.dataset.index || "0", 10);
    setImage(imgEl, imgs, (cur + 1) % imgs.length);
  }, intervalMs);
  container.dataset.timer = String(id);
}
function stopTimer(container) {
  const t = container.dataset.timer;
  if (t) {
    clearInterval(parseInt(t, 10));
    container.dataset.timer = "";
  }
}
// ===== Promedio dinámico =====
async function actualizarPromedio(salonId) {
  try {
    const res = await fetch(`/api/salones/${salonId}/comentarios`);
    const data = await res.json();
    const el = document.querySelector(`#salon-${salonId} .promedio`);
    if (!el) return;

    if (Array.isArray(data) && data.length > 0) {
      const suma = data.reduce((acc, c) => acc + Number(c.estrellas), 0);
      el.textContent = (suma / data.length).toFixed(1);
    } else {
      el.textContent = "Sin calificaciones";
    }
  } catch (e) {
    console.error("Error al actualizar promedio", e);
  }
}

// ===== Comentarios =====
async function cargarComentarios(salonId) {
  const cont = document.getElementById(`comentarios-${salonId}`);
  if (!cont) return;
  cont.textContent = "Cargando...";
  try {
    const res = await fetch(`/api/salones/${salonId}/comentarios`);
    const data = await res.json();
    cont.innerHTML = Array.isArray(data) && data.length > 0
      ? data.map(c => `
        <div class="comentario">
          <div><strong>${esc(c.usuario)}</strong> — ${esc(String(c.estrellas))} estrellas</div>
          <div>${esc(c.comentario)}</div>
          <small>${esc(c.fecha || "")}</small>
          <button class="admin-del" style="display:none" onclick="eliminarComentario(${Number(c.id)})">Eliminar (admin)</button>
        </div>
      `).join("")
      : "Sin comentarios aún.";
    if (sessionStorage.getItem("admin") === "true") mostrarBotonesAdmin();
  } catch (e) {
    cont.textContent = "Error al cargar comentarios.";
  }
}

async function enviarComentario(ev, salonId) {
  const form = ev.target;
  const msg = form.querySelector(".form-msg");
  const usuario = form.usuario.value.trim();
  const comentario = form.comentario.value.trim();
  const estrellas = form.estrellas.value;

  if (!usuario || !comentario) {
    msg.textContent = "Nombre y comentario son obligatorios.";
    msg.classList.add("error");
    return;
  } else {
    msg.classList.remove("error");
  }

  try {
    const res = await fetch(`/api/salones/${salonId}/comentarios`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, comentario, estrellas })
    });
    const data = await res.json();
    if (res.ok) {
      msg.textContent = "Comentario agregado.";
      msg.classList.remove("error");
      form.reset();
      cargarComentarios(salonId);
      actualizarPromedio(salonId);
    } else {
      msg.textContent = data.error || "Error al enviar.";
      msg.classList.add("error");
    }
  } catch (e) {
    msg.textContent = "Error de red.";
    msg.classList.add("error");
  }
}
// ===== Admin login =====
async function loginAdmin(ev) {
  ev.preventDefault();
  const form = ev.target;
  const msg = form.querySelector(".login-msg");
  const usuario = form.usuario.value.trim();
  const clave = form.clave.value.trim();

  try {
    const res = await fetch("/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ usuario, clave })
    });
    const data = await res.json();

    if (res.ok) {
      sessionStorage.setItem("admin", "true");
      msg.textContent = "Acceso concedido.";
      closeModal("modalLogin");
      mostrarBotonesAdmin();
      actualizarBotonAdmin();

      // Mostrar botón de sugerencias
      const verSugerenciasBtn = document.getElementById("verSugerenciasBtn");
      if (verSugerenciasBtn) {
        verSugerenciasBtn.style.display = "inline-block";
      }
    } else {
      msg.textContent = data.error || "Credenciales incorrectas.";
    }
  } catch (e) {
    msg.textContent = "Error de red.";
  }
}


// ===== Controles de visibilidad de botones admin =====
function mostrarBotonesAdmin() {
  document.querySelectorAll(".admin-del").forEach(btn => {
    btn.style.display = "inline-block";
  });
}
function ocultarBotonesAdmin() {
  document.querySelectorAll(".admin-del").forEach(btn => {
    btn.style.display = "none";
  });
}

// ===== Botón Admin dinámico =====
function actualizarBotonAdmin() {
  const btn = document.getElementById("adminBtn");
  if (!btn) return;
  btn.textContent = sessionStorage.getItem("admin") === "true"
    ? "Cerrar sesión"
    : "Login Admin";
}

// ===== Toggle admin (abrir login / cerrar sesión) =====
function toggleAdmin() {
  if (sessionStorage.getItem("admin") === "true") {
    // --- Cerrar sesión ---
    sessionStorage.removeItem("admin");
    ocultarBotonesAdmin();
    actualizarBotonAdmin();

    // limpiar formulario de login
    const adminLoginForm = document.getElementById("adminLoginForm");
    if (adminLoginForm) adminLoginForm.reset();

    // Ocultar botón de sugerencias
    const verSugerenciasBtn = document.getElementById("verSugerenciasBtn");
    if (verSugerenciasBtn) {
      verSugerenciasBtn.style.display = "none";
    }

    // mostrar modal de despedida
    document.getElementById("modalLogout").style.display = "grid";
  } else {
    // abrir modal de login solo si el usuario lo pide
    openModal("modalLogin");
  }
}

// Exponer funciones globales si usas onclick en HTML
window.toggleAdmin = toggleAdmin;
window.openModal = openModal;
window.closeModal = closeModal;
window.eliminarComentario = eliminarComentario;




document.addEventListener("DOMContentLoaded", () => {
  const adminBtn = document.getElementById("adminBtn");
  const verSugerenciasBtn = document.getElementById("verSugerenciasBtn");
  const modalLogin = document.getElementById("modalLogin");
  const adminLoginForm = document.getElementById("adminLoginForm");
  const modalLogout = document.getElementById("modalLogout");
  const modalSugerencias = document.getElementById("modalSugerencias");
  const listaSugerencias = document.getElementById("listaSugerencias");
  const sugerenciasMsg = document.querySelector(".sugerencias-msg");

  // ===== Toggle admin (abrir login / cerrar sesión) =====
  adminBtn.addEventListener("click", () => {
    if (sessionStorage.getItem("admin") === "true") {
      // --- Cerrar sesión ---
      sessionStorage.removeItem("admin");
      adminLoginForm.reset();
      adminBtn.textContent = "Login Admin";
      verSugerenciasBtn.style.display = "none";
      modalLogout.style.display = "grid";
    } else {
      modalLogin.style.display = "grid";
    }
  });

  // ===== Ver sugerencias =====
  verSugerenciasBtn.addEventListener("click", async () => {
    try {
      const res = await fetch("/admin/salones-pendientes");
      const data = await res.json();
      if (!res.ok) {
        sugerenciasMsg.textContent = data.error || "No autorizado.";
        return;
      }
      renderSugerencias(data);
      modalSugerencias.style.display = "grid";
    } catch {
      sugerenciasMsg.textContent = "Error de red al cargar sugerencias.";
    }
  });

  function renderSugerencias(salones) {
    listaSugerencias.innerHTML = "";
    if (!salones.length) {
      listaSugerencias.innerHTML = "<p>No hay sugerencias pendientes.</p>";
      return;
    }
    salones.forEach(s => {
      const imgs = safeParseImages(s.imagenes);
      const item = document.createElement("div");
      item.className = "sugerencia-item";
      item.innerHTML = `
        <h4>${s.nombre}</h4>
        <p><strong>Dirección:</strong> ${s.direccion}</p>
        <p><strong>Teléfono:</strong> ${s.telefono}</p>
        ${imgs.length ? `<div class="thumbs">${imgs.map(src => `<img src="/static/${src}" alt="${s.nombre}">`).join("")}</div>` : ""}
        <div class="acciones">
          <button class="aprobar" data-id="${s.id}">Aprobar</button>
          <button class="denegar" data-id="${s.id}">Denegar</button>
        </div>
      `;
      listaSugerencias.appendChild(item);
    });
  }

  function safeParseImages(value) {
    try {
      const arr = typeof value === "string" ? JSON.parse(value) : value;
      return Array.isArray(arr) ? arr : [];
    } catch {
      return [];
    }
  }

  // ===== Delegación de eventos para botones Aprobar/Denegar =====
  listaSugerencias.addEventListener("click", async e => {
    const btn = e.target;
    if (!btn.dataset.id) return;
    const id = btn.dataset.id;

    if (btn.classList.contains("aprobar")) {
      await operarPendiente(id, "aceptar");
    }
    if (btn.classList.contains("denegar")) {
      await operarPendiente(id, "denegar");
    }
  });



  async function operarPendiente(id, accion) {
    try {
      const res = await fetch(`/admin/salones-pendientes/${id}/${accion}`, { method: "POST" });
      const data = await res.json();

      if (res.ok) {
        // refrescar lista
        const resList = await fetch("/admin/salones-pendientes");
        const listData = await resList.json();
        renderSugerencias(listData);

        if (accion === "aceptar") location.reload();

        sugerenciasMsg.textContent = data.mensaje || "Operación realizada.";
      } else {
        sugerenciasMsg.textContent = data.error || "Operación fallida.";
      }
    } catch {
      sugerenciasMsg.textContent = "Error de red al operar.";
    }
  }
});


  // ===== Al enviar el formulario de login =====
  adminLoginForm.addEventListener("submit", async e => {
    e.preventDefault();
    const formData = new FormData(adminLoginForm);
    const usuario = formData.get("usuario");
    const clave = formData.get("clave");

    try {
      const res = await fetch("/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario, clave })
      });
      const data = await res.json();

      if (res.ok) {
        sessionStorage.setItem("admin", "true");
        modalLogin.style.display = "none";
        verSugerenciasBtn.style.display = "inline-block";
        adminBtn.textContent = "Cerrar sesión";
      } else {
        document.querySelector(".login-msg").textContent = data.error || "Error de login";
      }
    } catch {
      document.querySelector(".login-msg").textContent = "Error de red.";
    }
  });

// ===== Sugerir salón =====
async function sugerirSalon(ev) {
  ev.preventDefault();
  const form = ev.target;
  const msg = form.querySelector(".sugerir-msg");
  const fd = new FormData(form);

  try {
    const res = await fetch("/sugerir", { method: "POST", body: fd });
    const data = await res.json();

    if (res.ok) {
      msg.textContent = "Sugerencia enviada correctamente.";
      msg.classList.remove("error");
      form.reset();
      closeModal("modalSugerir"); // si usas modal
    } else {
      msg.textContent = data.error || "Error al enviar sugerencia.";
      msg.classList.add("error");
    }
  } catch {
    msg.textContent = "Error de red.";
    msg.classList.add("error");
  }
}

// Enganchar al formulario
document.getElementById("sugerirForm").addEventListener("submit", sugerirSalon);


  // Al presionar "Ver sugerencias"
  verSugerenciasBtn.addEventListener("click", async () => {
    const res = await fetch("/admin/salones-pendientes");
    const data = await res.json();
    if (res.ok) {
      mostrarSugerencias(data);
    } else {
      alert(data.error || "No autorizado");
    }
  });

// Función para renderizar sugerencias
function mostrarSugerencias(salones) {
  const listaSugerencias = document.getElementById("listaSugerencias");
  const sugerenciasMsg = document.querySelector(".sugerencias-msg");

  listaSugerencias.innerHTML = "";

  if (!salones.length) {
    listaSugerencias.innerHTML = "<p>No hay sugerencias pendientes.</p>";
    return;
  }

  salones.forEach(s => {
    const card = document.createElement("div");
    card.className = "sugerencia-card";
    card.innerHTML = `
      <h3>${s.nombre}</h3>
      <p><strong>Dirección:</strong> ${s.direccion}</p>
      <p><strong>Teléfono:</strong> ${s.telefono}</p>
      <p><strong>Mapa:</strong> <a href="${s.mapa_url}" target="_blank">Ver</a></p>
      <p><strong>Imágenes:</strong> ${s.imagenes}</p>
      <div class="acciones">
        <button class="aprobar" data-id="${s.id}">Aprobar</button>
        <button class="denegar" data-id="${s.id}">Denegar</button>
      </div>
    `;
    listaSugerencias.appendChild(card);
  });

  document.getElementById("modalSugerencias").style.display = "grid";
}

  // Listeners para aprobar/denegar
  contenedor.addEventListener("click", async e => {
    if (e.target.classList.contains("aprobar")) {
      const id = e.target.dataset.id;
      const res = await fetch(`/admin/salones-pendientes/${id}/aceptar`, { method: "POST" });
      alert((await res.json()).mensaje);
    }
    if (e.target.classList.contains("denegar")) {
      const id = e.target.dataset.id;
      const res = await fetch(`/admin/salones-pendientes/${id}/denegar`, { method: "POST" });
      alert((await res.json()).mensaje);
    }
  });


// ===== Eliminar comentario (solo admin) =====
async function eliminarComentario(comentarioId) {
  if (sessionStorage.getItem("admin") !== "true") {
    alert("Acceso restringido para administradores.");
    return;
  }
  try {
    const res = await fetch(`/api/comentarios/${comentarioId}`, { method: "DELETE" });
    const data = await res.json();
    if (res.ok) {
      // Recalcular desde el contexto del botón
      const btn = document.querySelector(`button[onclick="eliminarComentario(${Number(comentarioId)})"]`);
      const salonSection = btn?.closest(".salon");
      const salonId = salonSection ? parseInt(salonSection.id.split("-")[1], 10) : null;
      if (salonId) {
        cargarComentarios(salonId);
        actualizarPromedio(salonId);
      }
    } else {
      alert(data.error || "No se pudo eliminar el comentario.");
    }
  } catch (e) {
    alert("Error de red al eliminar el comentario.");
  }
}

// ===== Sugerir salón =====
async function sugerirSalon(ev) {
  ev.preventDefault();
  const form = ev.target;
  const msg = form.querySelector(".sugerir-msg");

  const fd = new FormData(form);

  try {
    const res = await fetch("/sugerir", {
      method: "POST",
      body: fd
    });
    const data = await res.json();

    if (res.ok) {
      msg.textContent = "Sugerencia enviada correctamente.";
      msg.classList.remove("error");
      form.reset();
      closeModal("modalSugerir"); // si usas un modal para sugerir
    } else {
      msg.textContent = data.error || "Error al enviar sugerencia.";
      msg.classList.add("error");
    }
  } catch (e) {
    msg.textContent = "Error de red.";
    msg.classList.add("error");
  }
}


// ===== Para previsualizar las imagenes que se estan sugeriendo como maximo 3 =====
document.addEventListener("DOMContentLoaded", () => {
  const inputImagenes = document.getElementById("imagenes");
  const preview = document.getElementById("preview");

  inputImagenes.addEventListener("change", () => {
    preview.innerHTML = "";
    const files = Array.from(inputImagenes.files);

    if (files.length > 3) {
      alert("Solo puedes subir hasta 3 imágenes");
      inputImagenes.value = "";
      return;
    }

    files.forEach(file => {
      const reader = new FileReader();
      reader.onload = e => {
        const img = document.createElement("img");
        img.src = e.target.result;
        preview.appendChild(img);
      };
      reader.readAsDataURL(file);
    });
  });
});

// ==================== ELIMINAR SALÓN ====================
document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".admin-del");
  if (!btn) return;

  if (sessionStorage.getItem("admin") !== "true") {
    alert("No autorizado");
    return;
  }

  const salonId = btn.dataset.id;
  if (!salonId) return;

  if (!confirm("¿Seguro que deseas eliminar este salón?")) return;

  try {
    const res = await fetch(`/admin/salones/${salonId}/eliminar`, {
      method: "POST"
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.error || "No se pudo eliminar el salón");
      return;
    }

    // eliminar del DOM sin recargar
    document.getElementById(`salon-${salonId}`)?.remove();
    alert("Salón eliminado correctamente ");

  } catch {
    alert("Error de conexión");
  }
});













