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
    sessionStorage.removeItem("admin");
    ocultarBotonesAdmin();
    actualizarBotonAdmin();
    alert("Sesión cerrada.");
  } else {
    openModal("modalLogin");
  }
}

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

  const nombre = form.nombre.value.trim();
  const direccion = form.direccion.value.trim();
  const telefono = form.telefono.value.trim();
  const mapa_url = form.mapa_url.value.trim();
  const imagenes = form.imagenes.value.trim();

  if (!nombre || !direccion || !telefono || !mapa_url || !imagenes) {
    msg.textContent = "Todos los campos son obligatorios.";
    msg.classList.add("error");
    return;
  } else {
    msg.classList.remove("error");
  }

  try {
    const res = await fetch("/api/sugerir", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, direccion, telefono, mapa_url, imagenes })
    });
    const data = await res.json();
    if (res.ok) {
      msg.textContent = "Sugerencia enviada correctamente.";
      form.reset();
      closeModal("modalSugerir");
    } else {
      msg.textContent = data.error || "Error al enviar sugerencia.";
      msg.classList.add("error");
    }
  } catch (e) {
    msg.textContent = "Error de red.";
    msg.classList.add("error");
  }
}


